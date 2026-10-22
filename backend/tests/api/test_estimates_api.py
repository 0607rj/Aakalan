"""API tests for the M1 flow: project → requirements → questionnaire → components → estimate →
trace / scenarios / re-price, plus role checks, margin redaction and org isolation."""

import json
from datetime import UTC, datetime
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import hash_password
from app.models import Estimate, Organisation, Requirement, Role, User
from app.models.base import utcnow
from app.services.seeding.database import seed_demo_project
from app.services.seeding.golden import expected_path
from app.services.seeding.reference import load_reference
from tests.conftest import TEST_PASSWORD, login

RUNS = 500
H = dict[str, str]


def make_project(client: TestClient, headers: H, name: str = "Test portal") -> dict[str, Any]:
    r = client.post("/projects", json={"name": name, "buyer_type": "psu"}, headers=headers)
    assert r.status_code == 201, r.text
    body: dict[str, Any] = r.json()
    return body


def add_requirement(client: TestClient, headers: H, pid: str, **kw: Any) -> dict[str, Any]:
    payload = {
        "text": "Vendors shall register online.",
        "category": "functional",
        "clarity_score": 4,
        "source_refs": [{"clause_ref": "3.1", "page": 8}],
        **kw,
    }
    r = client.post(f"/projects/{pid}/requirements", json=payload, headers=headers)
    assert r.status_code == 201, r.text
    body: dict[str, Any] = r.json()
    return body


def ready_project(client: TestClient, headers: H) -> tuple[dict[str, Any], dict[str, Any]]:
    project = make_project(client, headers)
    req = add_requirement(client, headers, project["id"])
    comps = [
        {"catalog_key": "registration_empanelment", "size": "M", "requirement_ids": [req["id"]]},
        {"catalog_key": "ai_chatbot_rag", "size": "S"},
    ]
    r = client.put(
        f"/projects/{project['id']}/components", json={"components": comps}, headers=headers
    )
    assert r.status_code == 200, r.text
    answers = [{"key": "users_total", "value": 5000, "requirement_ids": [req["id"]]}]
    r = client.put(
        f"/projects/{project['id']}/questionnaire", json={"answers": answers}, headers=headers
    )
    assert r.status_code == 200, r.text
    return project, req


def estimate(client: TestClient, headers: H, pid: str, **kw: Any) -> dict[str, Any]:
    r = client.post(
        f"/projects/{pid}/estimates",
        json={"seed": 11, "monte_carlo_runs": RUNS, **kw},
        headers=headers,
    )
    assert r.status_code == 201, r.text
    body: dict[str, Any] = r.json()
    return body


def test_full_flow_with_traces(client: TestClient, estimator_headers: H) -> None:
    project, req = ready_project(client, estimator_headers)
    est = estimate(client, estimator_headers, project["id"])
    assert est["version"] == 1 and est["feasible"]
    assert est["rate_card_version"] and est["calibration"]["status"] == "uncalibrated"
    assert est["p10_paise"] <= est["p50_paise"] <= est["p90_paise"]
    assert est["top_drivers_text"]
    reg = next(ln for ln in est["lines"] if ln["bucket"] == "build.module_development")
    assert reg["requirement_ids"] == [req["id"]]
    for line in est["lines"]:
        r = client.get(
            f"/estimates/{est['id']}/lines/{line['id']}/trace", headers=estimator_headers
        )
        assert r.status_code == 200, line["line_key"]
        body = r.json()
        if not line["redacted"]:
            assert body["trace"]["formula_id"] == line["formula_id"]
            assert body["trace"]["formula"]
    trace = client.get(
        f"/estimates/{est['id']}/lines/{reg['id']}/trace", headers=estimator_headers
    ).json()
    assert trace["trace"]["requirements"][0]["clause_ref"] == "3.1"
    assert trace["trace"]["requirements"][0]["page"] == 8
    assert trace["trace"]["component"]["catalog_key"] == "registration_empanelment"
    assert any(r["key"] == "role.developer" for r in trace["trace"]["rate_items"])


def test_same_inputs_and_seed_give_identical_estimates(
    client: TestClient, estimator_headers: H
) -> None:
    project, _ = ready_project(client, estimator_headers)
    a = estimate(client, estimator_headers, project["id"])
    b = estimate(client, estimator_headers, project["id"])
    assert b["version"] == a["version"] + 1
    keys = ("likely_paise", "p10_paise", "p50_paise", "p90_paise")
    assert [a[k] for k in keys] == [b[k] for k in keys]
    assert [ln["likely_paise"] for ln in a["lines"]] == [ln["likely_paise"] for ln in b["lines"]]


def test_saved_estimate_unchanged_when_catalog_v6_arrives(
    client: TestClient, estimator_headers: H, db: Session
) -> None:
    """An estimate on catalog v5 keeps its AI savings on every block and never changes; the
    next one uses the newest catalog (source eras; from parameters v18 unknown-era data counts
    as pre-AI, so the saving is taken off it as before)."""
    project, _ = ready_project(client, estimator_headers)
    old = estimate(client, estimator_headers, project["id"], catalog_version="v5")
    labour = {ln["formula_id"] for ln in old["lines"] if ln["component_instance_id"]}
    assert old["catalog_version"] == "v5" and labour == {"component_labour.v2"}
    new = estimate(client, estimator_headers, project["id"])
    labour = {ln["formula_id"] for ln in new["lines"] if ln["component_instance_id"]}
    # v3: source eras (catalog v6); v4 adds the reuse factor (parameters v19)
    assert int(new["catalog_version"][1:]) >= 6 and labour == {"component_labour.v4"}

    again = client.get(f"/estimates/{old['id']}", headers=estimator_headers).json()
    keys = ("likely_paise", "p10_paise", "p50_paise", "p90_paise")
    assert [again[k] for k in keys] == [old[k] for k in keys]
    assert [ln["likely_paise"] for ln in again["lines"]] == [
        ln["likely_paise"] for ln in old["lines"]
    ]
    rows = {
        e.id: e for e in db.scalars(select(Estimate).where(Estimate.project_id == project["id"]))
    }
    assert rows[old["id"]].result["era_sensitivity"] is None  # v5 records no source eras
    # parameters v18: unknown era is already priced as pre-AI, so there is no other reading
    assert rows[new["id"]].result["era_sensitivity"] is None


def test_margin_redacted_for_estimator_visible_to_finance(
    client: TestClient, estimator_headers: H, finance_headers: H
) -> None:
    project, _ = ready_project(client, estimator_headers)
    est = estimate(client, estimator_headers, project["id"])
    margin = next(ln for ln in est["lines"] if ln["bucket"] == "commercial.margin")
    assert margin["redacted"] and margin["likely_paise"] is None and not est["margin_visible"]
    trace = client.get(
        f"/estimates/{est['id']}/lines/{margin['id']}/trace", headers=estimator_headers
    )
    assert trace.json()["trace"] is None
    q = client.get(f"/projects/{project['id']}/questionnaire", headers=estimator_headers).json()
    assert next(f for f in q["fields"] if f["key"] == "margin_percent")["value"] is None

    seen = client.get(f"/estimates/{est['id']}", headers=finance_headers).json()
    margin = next(ln for ln in seen["lines"] if ln["bucket"] == "commercial.margin")
    assert not margin["redacted"] and margin["likely_paise"] > 0 and seen["margin_visible"]


def test_margin_answer_is_finance_only(
    client: TestClient, estimator_headers: H, finance_headers: H
) -> None:
    project = make_project(client, estimator_headers)
    url = f"/projects/{project['id']}/questionnaire"
    body = {"answers": [{"key": "margin_percent", "value": 0.2}]}
    assert client.put(url, json=body, headers=estimator_headers).status_code == 403
    assert client.put(url, json=body, headers=finance_headers).status_code == 200
    # an estimator saving other answers keeps the finance-set margin
    r = client.put(
        url, json={"answers": [{"key": "om_years", "value": 2}]}, headers=estimator_headers
    )
    assert r.status_code == 200
    fields = {f["key"]: f for f in client.get(url, headers=finance_headers).json()["fields"]}
    assert fields["margin_percent"]["value"] == 0.2 and fields["om_years"]["value"] == 2


def test_questionnaire_validation(client: TestClient, estimator_headers: H) -> None:
    project = make_project(client, estimator_headers)
    url = f"/projects/{project['id']}/questionnaire"
    q = client.get(url, headers=estimator_headers).json()
    fields = {f["key"]: f for f in q["fields"]}
    assert fields["om_years"]["source"] == "default" and fields["om_years"]["value"] == 3
    bad = client.put(
        url, json={"answers": [{"key": "uptime_sla", "value": "100"}]}, headers=estimator_headers
    )
    assert bad.status_code == 422
    unknown = client.put(
        url, json={"answers": [{"key": "nope", "value": 1}]}, headers=estimator_headers
    )
    assert unknown.status_code == 422


def test_human_review_required_before_pricing(
    client: TestClient, estimator_headers: H, db: Session
) -> None:
    project = make_project(client, estimator_headers)
    url = f"/projects/{project['id']}/estimates"
    assert client.post(url, json={}, headers=estimator_headers).status_code == 409  # no components
    comps = {"components": [{"catalog_key": "notifications", "size": "S"}]}
    client.put(f"/projects/{project['id']}/components", json=comps, headers=estimator_headers)
    org_id = client.get("/auth/me", headers=estimator_headers).json()["org_id"]
    db.add(
        Requirement(
            org_id=org_id,
            project_id=project["id"],
            code="REQ-900",
            text_normalised="Extracted, not reviewed",
            category="functional",
            clarity_score=3,
            status="extracted",
            source_refs=[{"clause_ref": "9.9", "page": 1}],
        )
    )
    db.commit()
    r = client.post(url, json={"monte_carlo_runs": RUNS}, headers=estimator_headers)
    assert r.status_code == 409 and "REQ-900" in r.json()["detail"]
    confirm = client.post(
        f"/projects/{project['id']}/requirements/confirm", json={}, headers=estimator_headers
    )
    assert confirm.status_code == 200
    assert (
        client.post(url, json={"monte_carlo_runs": RUNS}, headers=estimator_headers).status_code
        == 201
    )


def test_requirement_edit_and_reject(client: TestClient, estimator_headers: H) -> None:
    project = make_project(client, estimator_headers)
    req = add_requirement(client, estimator_headers, project["id"])
    assert req["status"] == "confirmed" and req["code"] == "REQ-001"
    r = client.patch(
        f"/requirements/{req['id']}", json={"text": "Changed"}, headers=estimator_headers
    )
    assert r.json()["status"] == "edited" and r.json()["text"] == "Changed"
    r = client.patch(
        f"/requirements/{req['id']}", json={"status": "rejected"}, headers=estimator_headers
    )
    assert r.json()["status"] == "rejected"
    missing_ref = {"text": "x", "source_refs": []}
    assert (
        client.post(
            f"/projects/{project['id']}/requirements", json=missing_ref, headers=estimator_headers
        ).status_code
        == 422
    )


def test_viewer_is_read_only(client: TestClient, estimator_headers: H, viewer_headers: H) -> None:
    project, _ = ready_project(client, estimator_headers)
    est = estimate(client, estimator_headers, project["id"])
    assert client.get(f"/estimates/{est['id']}", headers=viewer_headers).status_code == 200
    assert client.post("/projects", json={"name": "x"}, headers=viewer_headers).status_code == 403
    r = client.post(f"/projects/{project['id']}/estimates", json={}, headers=viewer_headers)
    assert r.status_code == 403


def test_reprice_creates_new_version(
    client: TestClient, estimator_headers: H, admin_headers: H
) -> None:
    project, _ = ready_project(client, estimator_headers)
    est = estimate(client, estimator_headers, project["id"])
    current = client.get(f"/admin/rate-cards/{est['rate_card_version']}", headers=admin_headers)
    base = current.json()
    today = datetime.now(UTC).date().isoformat()  # newest effective date -> becomes the active card
    v2 = {**base, "version": "v2-test", "effective_date": today, "items": [
        {**i, "amount": str(float(i["amount"]) * 1.1)} if i["key"] == "role.developer" else i
        for i in base["items"]
    ]}  # fmt: skip
    assert client.post("/admin/rate-cards", json=v2, headers=estimator_headers).status_code == 403
    assert client.post("/admin/rate-cards", json=v2, headers=admin_headers).status_code == 201
    assert client.post("/admin/rate-cards", json=v2, headers=admin_headers).status_code == 409
    r = client.post(f"/estimates/{est['id']}/reprice", headers=estimator_headers)
    assert r.status_code == 201, r.text
    new = r.json()
    assert new["version"] == est["version"] + 1 and new["parent_estimate_id"] == est["id"]
    assert new["rate_card_version"] == "v2-test" and new["seed"] == est["seed"]
    assert new["likely_paise"] > est["likely_paise"]
    old = client.get(f"/estimates/{est['id']}", headers=estimator_headers).json()
    assert old["likely_paise"] == est["likely_paise"]
    assert old["rate_card_version"] == est["rate_card_version"]


def test_scenarios_side_by_side(client: TestClient, estimator_headers: H) -> None:
    project, _ = ready_project(client, estimator_headers)
    est = estimate(client, estimator_headers, project["id"])
    body = {
        "scenarios": [
            {"name": "Indian cloud", "overrides": {"hosting_provider": "indian_cloud"}},
            {"name": "Self-hosted GPU", "overrides": {"ai_runtime_mode": "self_hosted_gpu"}},
            {"name": "On-prem", "overrides": {"hosting_provider": "on_prem"}},
        ]
    }
    r = client.post(f"/estimates/{est['id']}/scenarios", json=body, headers=estimator_headers)
    assert r.status_code == 200, r.text
    results = r.json()["results"]
    assert [x["name"] for x in results] == [
        "Baseline",
        "Indian cloud",
        "Self-hosted GPU",
        "On-prem",
    ]
    assert results[0]["totals"]["p50_paise"] != results[3]["totals"]["p50_paise"]


def test_org_isolation(client: TestClient, estimator_headers: H, db: Session) -> None:
    project, _ = ready_project(client, estimator_headers)
    est = estimate(client, estimator_headers, project["id"])
    other = Organisation(name="Other SI")
    db.add(other)
    db.flush()
    db.add(User(org_id=other.id, email="spy@other.local", full_name="Spy", role=Role.ADMIN,
                password_hash=hash_password(TEST_PASSWORD),
                email_verified_at=utcnow()))  # fmt: skip
    db.commit()
    spy = login(client, "spy@other.local")
    assert client.get(f"/projects/{project['id']}", headers=spy).status_code == 404
    assert client.get(f"/estimates/{est['id']}", headers=spy).status_code == 404
    line = est["lines"][0]["id"]
    assert client.get(f"/estimates/{est['id']}/lines/{line}/trace", headers=spy).status_code == 404
    assert all(p["id"] != project["id"] for p in client.get("/projects", headers=spy).json())


@pytest.mark.parametrize("path", ["/admin/rate-cards", "/admin/parameter-sets", "/catalog"])
def test_reference_endpoints(client: TestClient, estimator_headers: H, path: str) -> None:
    r = client.get(path, headers=estimator_headers)
    assert r.status_code == 200 and r.json()


def test_demo_project_reproduces_golden_base_case(
    client: TestClient, estimator_headers: H, db: Session
) -> None:
    """The DB path (snapshot built from rows) prices exactly like the golden fixture."""
    org_id = client.get("/auth/me", headers=estimator_headers).json()["org_id"]
    org = db.get(Organisation, org_id)
    assert org is not None
    project = seed_demo_project(db, org, load_reference(get_settings().seeds_dir))
    db.commit()
    assert project is not None
    est = estimate(
        client,
        estimator_headers,
        project.id,
        as_of_date="2026-10-15",
        rate_card_version="v1",
        parameter_set_version="v1",
        catalog_version="v1",  # the golden fixtures are priced on catalog v1
    )
    golden = json.loads(expected_path("medium").read_text(encoding="utf-8"))
    assert est["likely_paise"] == golden["totals"]["likely_paise"]
    assert est["timeline"]["status"] == "compressed"


def test_unknown_rate_key_is_a_clear_422(client: TestClient, estimator_headers: H) -> None:
    project, _ = ready_project(client, estimator_headers)
    answers = [{"key": "onsite_resources", "value": [{"role": "role.astronaut", "count": 1}]}]
    url = f"/projects/{project['id']}/questionnaire"
    assert client.put(url, json={"answers": answers}, headers=estimator_headers).status_code == 200
    r = client.post(f"/projects/{project['id']}/estimates", json={}, headers=estimator_headers)
    assert r.status_code == 422 and "role.astronaut" in r.json()["detail"]

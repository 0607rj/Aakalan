"""Quick estimate: plain form -> priced estimate -> plain summary."""

from typing import Any

from fastapi.testclient import TestClient

from app.services.quick.config import quick_config

H = dict[str, str]


def quick(client: TestClient, headers: H, **body: Any) -> Any:
    payload = {"name": "Quick test portal", "features": ["online_forms", "ai_chatbot"], **body}
    return client.post("/quick-estimates", json=payload, headers=headers)


def test_options_are_plain_language(client: TestClient, admin_headers: H) -> None:
    r = client.get("/quick-estimate/options", headers=admin_headers)
    assert r.status_code == 200
    body = r.json()
    assert {f["key"] for f in body["features"]} >= {"online_forms", "ai_chatbot", "payments"}
    scale = next(q for q in body["questions"] if q["key"] == "scale")
    assert scale["default"] == "medium" and len(scale["options"]) == 3


def test_quick_estimate_summary(client: TestClient, admin_headers: H) -> None:
    r = quick(client, admin_headers, choices={"scale": "small", "support_years": 3})
    assert r.status_code == 201, r.text
    s = r.json()
    assert s["feasible"] and s["indicative"]
    assert s["low_paise"] <= s["likely_paise"] <= s["high_paise"]
    assert sum(p["amount_paise"] for p in s["parts"]) == s["planned_paise"]
    assert s["risk_allowance_paise"] == s["likely_paise"] - s["planned_paise"]
    assert s["support_years"] == 3 and "3 years" in s["parts"][2]["label"]
    assert s["biggest_uncertainty"].startswith("The biggest unknown is")
    assert s["features"][0].startswith("Online application")
    # the detailed estimate is the same engine output, with ticked features as requirements
    detail = client.get(f"/estimates/{s['estimate_id']}", headers=admin_headers).json()
    assert detail["p50_paise"] == s["likely_paise"]
    chatbot = next(ln for ln in detail["lines"] if ln["bucket"] == "build.ai_ml")
    trace = client.get(
        f"/estimates/{s['estimate_id']}/lines/{chatbot['id']}/trace", headers=admin_headers
    ).json()["trace"]
    assert trace["requirements"][0]["clause_ref"].startswith("Feature: AI chatbot")
    again = client.get(f"/estimates/{s['estimate_id']}/summary", headers=admin_headers).json()
    assert again["likely_paise"] == s["likely_paise"]


def test_more_features_cost_more(client: TestClient, admin_headers: H) -> None:
    few = quick(client, admin_headers, features=["online_forms"]).json()
    many = quick(
        client, admin_headers, features=["online_forms", "approval_workflow", "payments"]
    ).json()
    assert many["planned_paise"] > few["planned_paise"]


def test_no_chatbot_means_no_ai_running_cost(client: TestClient, admin_headers: H) -> None:
    s = quick(client, admin_headers, features=["online_forms"]).json()
    detail = client.get(f"/estimates/{s['estimate_id']}", headers=admin_headers).json()
    assert not [ln for ln in detail["lines"] if ln["bucket"] == "run.ai_runtime"]


def test_bad_input_is_rejected(client: TestClient, admin_headers: H) -> None:
    assert quick(client, admin_headers, features=["teleport"]).status_code == 422
    assert quick(client, admin_headers, choices={"scale": "huge"}).status_code == 422
    assert quick(client, admin_headers, choices={"colour": "blue"}).status_code == 422
    assert quick(client, admin_headers, features=[]).status_code == 422


def test_impossible_deadline_is_explained(client: TestClient, admin_headers: H) -> None:
    s = quick(client, admin_headers, deadline_months=1, choices={"scale": "large"}).json()
    assert not s["feasible"] and s["likely_paise"] is None and "deadline" in s["message"]


def test_list_shows_latest_estimates(client: TestClient, admin_headers: H) -> None:
    quick(client, admin_headers, name="Listed portal")
    names = [s["name"] for s in client.get("/quick-estimates", headers=admin_headers).json()]
    assert "Listed portal" in names


def test_every_mapped_component_exists_in_catalog(client: TestClient, admin_headers: H) -> None:
    cfg = quick_config()
    keys = {c["key"] for c in client.get("/catalog", headers=admin_headers).json()["components"]}
    mapped = set(cfg.base_components) | {k for f in cfg.features for k in f.components}
    mapped |= {k for o in cfg.questions["scale"].options for k in o.extra_components}
    assert mapped <= keys


def test_questions_ranked_by_price_impact(client: TestClient, admin_headers: H) -> None:
    body = {"name": "Impact", "features": ["online_forms", "ai_chatbot"], "choices": {}}
    r = client.post("/quick-estimate/impact", json=body, headers=admin_headers)
    assert r.status_code == 200, r.text
    ranked = r.json()
    impacts = [q["impact_paise"] for q in ranked]
    assert impacts == sorted(impacts, reverse=True) and impacts[0] > 0
    scale = next(q for q in ranked if q["key"] == "scale")
    prices = [o["likely_paise"] for o in scale["options"]]
    assert prices == sorted(prices)  # small < medium < large
    # nothing was saved
    assert all(
        s["name"] != "Impact" for s in client.get("/quick-estimates", headers=admin_headers).json()
    )
    with_years = client.post(
        "/quick-estimate/impact", json={**body, "overrides": {"om_years": 4}}, headers=admin_headers
    ).json()
    assert "support_years" not in {q["key"] for q in with_years}

"""A feature the catalog lacks: researched once (web sources checked on the page, else the AI's
analysis as catalog blocks), saved for the organisation and reused, without an AI key the
generic block as before. Never a real AI or a real web page."""

from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import hash_password
from app.llm.client import FakeClient, set_llm_client
from app.models import Organisation, Role, User
from app.models.base import utcnow
from app.services.research import library
from app.services.research.fetch import set_page_fetcher
from app.services.research.library import read_library
from tests.conftest import TEST_PASSWORD, login

H = dict[str, str]
PAGE = "Feature hours table. Fleet geofencing alerts: 120-200 hours. Other rows follow."


@pytest.fixture
def fakes() -> Iterator[list[str]]:
    calls: list[str] = []
    set_page_fetcher(lambda url, timeout, size: PAGE)
    yield calls
    set_llm_client(None)
    set_page_fetcher(None)


def ai(calls: list[str], web: list[dict[str, Any]], parts: list[dict[str, str]]) -> None:
    def respond(system: str, user: str) -> object:
        calls.append(user)
        if "Catalog blocks" in system:
            return {"section": "mobile", "description": "Analysed", "parts": parts}
        return {"section": "integrations", "description": "Geofencing", "sources": web}

    set_llm_client(FakeClient(respond))


def estimate(client: TestClient, headers: H, name: str, category: str = "module") -> Any:
    body = {
        "name": "Research test",
        "features": ["online_forms"],
        "custom_features": [{"name": name, "category": category, "size": "M"}],
    }
    r = client.post("/quick-estimates", json=body, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


def trace_key(client: TestClient, headers: H, s: Any, label: str) -> str:
    detail = client.get(f"/estimates/{s['estimate_id']}", headers=headers).json()
    line = next(ln for ln in detail["lines"] if ln["label"] == label)
    trace = client.get(
        f"/estimates/{s['estimate_id']}/lines/{line['id']}/trace", headers=headers
    ).json()["trace"]
    return str(trace["component"]["catalog_key"])


def retire_all(client: TestClient, headers: H) -> None:
    for b in client.get("/research-blocks", headers=headers).json():
        if b["status"] == "active":
            client.post(f"/research-blocks/{b['id']}/retire", headers=headers)


def test_web_research_is_saved_and_reused(
    client: TestClient, admin_headers: H, fakes: list[str]
) -> None:
    source = {
        "url": "https://example.com/cost-guide",
        "publisher": "Example Co",
        "title": "Cost guide",
        "label": "Fleet geofencing alerts",
        "quote": "Fleet geofencing alerts: 120-200 hours",
        "low": 120,
        "high": 200,
    }
    ai(fakes, [source], [])
    name = "Fleet geofencing alerts"
    s = estimate(client, admin_headers, name)
    assert trace_key(client, admin_headers, s, name) == "researched_alert_fleet_geofencing"
    [found] = s["researched"]
    assert found["method"] == "web" and found["sources"][0]["url"] == source["url"]
    blocks = client.get("/research-blocks", headers=admin_headers).json()
    block = next(b for b in blocks if b["key"] == "researched_alert_fleet_geofencing")
    assert block["status"] == "active" and block["section"] == "integrations"
    # 120 / 160 / 200 h x 0.9 / 8 h per day
    assert block["base_effort_pd"] == {"S": "13.5", "M": "18.0", "L": "22.5"}

    asked = len(fakes)
    again = estimate(client, admin_headers, "Geofencing alerts for fleet")
    assert len(fakes) == asked  # found in the catalog: no AI call
    assert again["researched"][0]["name"] == "Geofencing alerts for fleet"  # as typed

    # the form lists it under its section; ticked, it is sent with its block: no search
    options = client.get("/quick-estimate/options", headers=admin_headers).json()
    [listed] = [r for r in options["researched"] if r["name"] == name]
    assert listed["section"] == "integrations"
    assert listed["section_label"] == "Connections to other systems"
    ticked = {
        "name": "Research test",
        "features": ["online_forms"],
        "custom_features": [
            {
                "name": name,
                "category": listed["category"],
                "size": "M",
                "catalog_key": listed["catalog_key"],
            }
        ],
    }
    r = client.post("/quick-estimates", json=ticked, headers=admin_headers)
    assert r.status_code == 201 and len(fakes) == asked
    assert trace_key(client, admin_headers, r.json(), name) == listed["catalog_key"]

    retire_all(client, admin_headers)
    after = estimate(client, admin_headers, "Fleet geofencing alerts")
    assert after["researched"] == []  # retired: not searched again, the generic block prices it
    options = client.get("/quick-estimate/options", headers=admin_headers).json()
    assert all(r["name"] != name for r in options["researched"])  # retired: not offered


def test_analysis_when_no_page_checks_out(
    client: TestClient, admin_headers: H, fakes: list[str]
) -> None:
    wrong = {
        "url": "https://example.com/x",
        "label": "Drone flight logs",
        "quote": "q",
        "low": 999,
        "high": 1000,
    }
    ai(fakes, [wrong], [{"block": "push_notifications", "level": "standard", "why": "alerts"}])
    s = estimate(client, admin_headers, "Drone flight log uploads", category="mobile")
    [found] = s["researched"]
    assert found["method"] == "analysis" and found["section"] == "mobile"
    assert "push_notifications standard" in found["sources"][0]["label"]
    retire_all(client, admin_headers)


def test_nothing_usable_keeps_the_generic_block(
    client: TestClient, admin_headers: H, fakes: list[str]
) -> None:
    ai(fakes, [], [{"block": "not_a_block", "level": "basic"}])
    name = "Quantum ledger reconciliation"
    s = estimate(client, admin_headers, name)
    assert trace_key(client, admin_headers, s, name) == "custom_module"
    blocks = client.get("/research-blocks", headers=admin_headers).json()
    assert next(b for b in blocks if b["name"] == name)["status"] == "no_evidence"
    asked = len(fakes)
    estimate(client, admin_headers, name)
    assert len(fakes) == asked  # not searched again for retry_no_evidence_days


def test_without_ai_key_nothing_is_searched(client: TestClient, admin_headers: H) -> None:
    r = client.post(
        "/research-blocks",
        json={"name": "Satellite telemetry parser", "category": "integration"},
        headers=admin_headers,
    ).json()
    assert r == {"ai_available": False, "catalog_key": None, "block": None}
    known = client.post(
        "/research-blocks",
        json={"name": "Push notifications", "category": "module"},
        headers=admin_headers,
    ).json()
    assert known["catalog_key"] == "push_notifications"  # the catalog still answers


def test_unknown_catalog_key_is_refused(client: TestClient, admin_headers: H) -> None:
    body = {
        "name": "x",
        "features": ["online_forms"],
        "custom_features": [
            {"name": "Thing", "category": "module", "size": "M", "catalog_key": "nope"}
        ],
    }
    assert client.post("/quick-estimates", json=body, headers=admin_headers).status_code == 422


def other_company(client: TestClient, db: Session, email: str) -> H:
    other = Organisation(name=f"Other SI ({email})")
    db.add(other)
    db.flush()
    db.add(
        User(
            org_id=other.id,
            email=email,
            full_name="Other",
            role=Role.ADMIN,
            password_hash=hash_password(TEST_PASSWORD),
            email_verified_at=utcnow(),
        )
    )
    db.commit()
    return login(client, email)


def test_research_is_shared_with_every_company(
    client: TestClient, admin_headers: H, db: Session, fakes: list[str]
) -> None:
    """Researched once by one company, the feature joins the shared library (table and file):
    another company that types it is priced by it with no AI call of its own, but never sees
    it listed or named, since its name shows what the first company bids on (OPEN_QUESTIONS
    185)."""
    ai(fakes, [], [{"block": "push_notifications", "level": "standard", "why": "alerts"}])
    name = "Parcel locker pickup slots"
    first = estimate(client, admin_headers, name)
    [found] = first["researched"]
    key = trace_key(client, admin_headers, first, name)
    assert key.startswith("researched_") and found["section"] == "mobile"
    library = read_library(get_settings().resolved_research_library)
    [entry] = [e for e in library if e.key == key]
    assert entry.name == name and entry.method == "analysis" and entry.spec["key"] == key

    them = other_company(client, db, "research@other.local")
    asked = len(fakes)
    typed = "Pickup slots for parcel locker"
    theirs = estimate(client, them, typed)
    assert len(fakes) == asked  # priced from the library: no search
    assert trace_key(client, them, theirs, typed) == key
    assert [r["name"] for r in theirs["researched"]] == [typed]  # their words, not the block's
    options = client.get("/quick-estimate/options", headers=them).json()
    assert all(r["catalog_key"] != key for r in options["researched"])  # never listed
    catalog = client.get("/catalog", headers=them).json()["components"]
    assert all(c["key"] != key for c in catalog)
    assert client.get("/research-blocks", headers=them).json() == []
    mine = client.get("/quick-estimate/options", headers=admin_headers).json()
    assert [r["name"] for r in mine["researched"] if r["catalog_key"] == key] == [name]
    retire_all(client, admin_headers)


def test_sharing_off_keeps_each_company_to_its_own(
    client: TestClient,
    admin_headers: H,
    db: Session,
    fakes: list[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`research.share: false`: nothing new is shared and the shared blocks price nobody else."""
    monkeypatch.setattr(library, "sharing_on", lambda: False)
    ai(fakes, [], [{"block": "push_notifications", "level": "standard", "why": "alerts"}])
    name = "Cold storage temperature log"
    first = estimate(client, admin_headers, name)
    key = trace_key(client, admin_headers, first, name)
    assert all(e.key != key for e in read_library(get_settings().resolved_research_library))
    them = other_company(client, db, "private@other.local")
    asked = len(fakes)
    estimate(client, them, name)
    assert len(fakes) > asked  # not in the library: researched for them
    retire_all(client, admin_headers)
    retire_all(client, them)

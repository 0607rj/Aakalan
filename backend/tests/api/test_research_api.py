"""A feature the catalog lacks: researched once (web sources checked on the page, else the AI's
analysis as catalog blocks), saved for the organisation and reused, without an AI key the
generic block as before. Never a real AI or a real web page."""

from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.llm.client import FakeClient, set_llm_client
from app.services.research.fetch import set_page_fetcher

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
    assert again["researched"][0]["name"] == name
    retire_all(client, admin_headers)
    after = estimate(client, admin_headers, "Fleet geofencing alerts")
    assert after["researched"] == []  # retired: not searched again, the generic block prices it


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

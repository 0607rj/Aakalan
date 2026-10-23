"""Country (India / US) pricing, company settings and back-testing."""

from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.services.calibration.backtest import backtest, load_benchmarks, reference_for
from app.services.quick.config import quick_config
from app.services.seeding.reference import load_reference

H = dict[str, str]
BASE = {"name": "Country portal", "features": ["online_forms", "approval_workflow"]}


@pytest.fixture
def us_on(monkeypatch: pytest.MonkeyPatch) -> None:
    """The US is switched off in the shipped config; these tests switch it back on."""
    cfg = quick_config()
    countries = {k: c.model_copy(update={"enabled": True}) for k, c in cfg.countries.items()}
    on = cfg.model_copy(update={"countries": countries})
    monkeypatch.setattr("app.api.quick.quick_config", lambda: on)


def test_us_is_switched_off_by_default(client: TestClient, admin_headers: H) -> None:
    opts = client.get("/quick-estimate/options?country=us", headers=admin_headers).json()
    assert opts["country"] == "india"
    assert {c["key"] for c in opts["countries"]} == {"india"}
    r = client.post("/quick-estimates", json={**BASE, "country": "us"}, headers=admin_headers)
    assert r.status_code == 422 and "switched off" in r.text


def quick(client: TestClient, headers: H, **body: object) -> dict[str, object]:
    r = client.post("/quick-estimates", json={**BASE, **body}, headers=headers)
    assert r.status_code == 201, r.text
    out: dict[str, object] = r.json()
    return out


def test_us_estimate_is_in_dollars_without_gst(
    client: TestClient, admin_headers: H, us_on: None
) -> None:
    us = quick(client, admin_headers, country="us")
    india = quick(client, admin_headers, country="india")
    assert us["currency"] == "USD" and us["country"] == "us"
    assert india["currency"] == "INR"
    detail = client.get(f"/estimates/{us['estimate_id']}", headers=admin_headers).json()
    assert detail["rate_card_version"].startswith("us-")
    assert detail["parameter_set_version"].startswith("us-")
    tax = next(ln for ln in detail["lines"] if ln["bucket"] == "commercial.gst")
    assert tax["label"] == "Sales tax" and tax["likely_paise"] == 0
    dev = next(ln for ln in detail["lines"] if ln["bucket"] == "build.module_development")
    trace = client.get(
        f"/estimates/{detail['id']}/lines/{dev['id']}/trace", headers=admin_headers
    ).json()
    assert all(r["currency"] == "USD" for r in trace["trace"]["rate_items"])


def test_country_limits_hosting_options(client: TestClient, admin_headers: H, us_on: None) -> None:
    opts = client.get("/quick-estimate/options?country=us", headers=admin_headers).json()
    hosting = next(q for q in opts["questions"] if q["key"] == "hosting")
    assert "indian_cloud" not in {o["value"] for o in hosting["options"]}
    assert {c["key"] for c in opts["countries"]} == {"india", "us"}
    r = client.post(
        "/quick-estimates",
        json={**BASE, "country": "us", "choices": {"hosting": "indian_cloud"}},
        headers=admin_headers,
    )
    assert r.status_code == 422
    assert (
        client.post(
            "/quick-estimates", json={**BASE, "country": "mars"}, headers=admin_headers
        ).status_code
        == 422
    )


def test_company_settings_change_new_estimates(client: TestClient, admin_headers: H) -> None:
    before = quick(client, admin_headers)
    assert client.get("/settings", headers=admin_headers).json()["build_effort_multiplier"] == "1"
    lean = {
        "margin_percent": "0.05",
        "contingency_percent": "0.05",
        "build_effort_multiplier": "0.7",
    }
    r = client.put("/settings", json=lean, headers=admin_headers)
    assert r.status_code == 200, r.text
    try:
        after = quick(client, admin_headers)
        assert after["likely_paise"] < before["likely_paise"]  # type: ignore[operator]
        detail = client.get(f"/estimates/{after['estimate_id']}", headers=admin_headers).json()
        margin = next(ln for ln in detail["lines"] if ln["line_key"] == "commercial.margin/total")
        trace = client.get(
            f"/estimates/{detail['id']}/lines/{margin['id']}/trace", headers=admin_headers
        )
        assert any(
            d["key"] == "margin_percent" and d["value"] == "0.05"
            for d in trace.json()["trace"]["drivers"]
        )
        old = client.get(f"/estimates/{before['estimate_id']}", headers=admin_headers).json()
        assert old["p50_paise"] == before["likely_paise"]  # earlier estimates never change
    finally:
        client.put("/settings", json={}, headers=admin_headers)


def test_settings_validation(client: TestClient, admin_headers: H, estimator_headers: H) -> None:
    assert (
        client.put("/settings", json={"margin_percent": "2"}, headers=admin_headers).status_code
        == 422
    )
    assert client.put("/settings", json={}, headers=estimator_headers).status_code == 403


def test_benchmarks_load_and_backtest_runs() -> None:
    settings = get_settings()
    bench = load_benchmarks(Path(settings.seeds_dir) / "benchmarks" / "india.yaml")
    assert bench.country == "india" and len(bench.projects) >= 3
    report = backtest(
        quick_config(),
        bench,
        reference_for(load_reference(settings.seeds_dir), "india"),
        Decimal(1),
        Decimal(1),
        segment="commercial",
    )
    assert report.projects_used >= 1 and report.median_abs_error_percent is not None


def test_company_rates_and_ai_level_change_new_estimates(
    client: TestClient, admin_headers: H
) -> None:
    roles = client.get("/settings/roles", headers=admin_headers).json()
    developer = next(r for r in roles if r["key"] == "role.developer")
    assert float(developer["market_rupees_per_day"]) > 0
    before = quick(client, admin_headers)
    double = str(float(developer["market_rupees_per_day"]) * 2)
    body = {"role_day_rates": {"role.developer": double}, "team_ai_maturity": "none"}
    assert client.put("/settings", json=body, headers=admin_headers).status_code == 200
    after = quick(client, admin_headers)
    assert int(str(after["likely_paise"])) > int(str(before["likely_paise"]))
    detail = client.get(f"/estimates/{after['estimate_id']}", headers=admin_headers).json()
    assert detail["rate_card_version"].endswith("+company")
    old = client.get(f"/estimates/{before['estimate_id']}", headers=admin_headers).json()
    assert old["p50_paise"] == before["likely_paise"]  # past estimates never change
    reprice = client.post(f"/estimates/{after['estimate_id']}/reprice", headers=admin_headers)
    assert reprice.status_code == 201, reprice.text
    assert after["traditional_paise"] is None  # the company's AI level: priced without AI
    client.put("/settings", json={}, headers=admin_headers)

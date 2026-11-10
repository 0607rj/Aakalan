"""OPEN_QUESTIONS 226: where every price comes from, read from the engine's trace, for any
project: every results row has its sources, every source says what it is, the builder's
profit is shown to everyone with its source (227), the AI saving names its studies, and the
PDF and Excel carry the same list."""

import io
from typing import Any

import openpyxl
from fastapi.testclient import TestClient

from app.services.quick.config import quick_config
from app.services.quick.sources import rate_title

H = dict[str, str]


def _estimate(client: TestClient, headers: H, features: list[str]) -> Any:
    r = client.post(
        "/quick-estimates",
        json={"name": "Sources test", "features": features, "choices": {"support_years": 2}},
        headers=headers,
    )
    assert r.status_code == 201, r.text
    return r.json()


def _sources(client: TestClient, headers: H, estimate_id: str) -> Any:
    r = client.get(f"/estimates/{estimate_id}/sources", headers=headers)
    assert r.status_code == 200, r.text
    return r.json()


def test_every_row_of_any_project_has_its_sources(client: TestClient, admin_headers: H) -> None:
    for features in (["online_forms", "ai_chatbot"], ["payments", "bookings", "mobile_app"]):
        s = _estimate(client, admin_headers, features)
        out = _sources(client, admin_headers, s["estimate_id"])
        numbers = {src["n"] for src in out["sources"]}
        assert numbers == set(range(1, len(numbers) + 1))
        rows = {r["row"]: r for r in out["rows"]}
        for item in s["cost_items"]:
            row = rows[f"item:{item['group']}:{item['key']}"]
            assert row["sources"] and set(row["sources"]) <= numbers, row["row"]
        for feature in s["feature_costs"]:
            # every feature row, the standard building blocks too, names its sources
            assert rows[f"feature:{feature['label']}"]["sources"], feature["label"]
            if not feature["label"].startswith("Standard building blocks"):
                assert rows[f"feature:{feature['label']}"]["asked"]  # the feature asked for it
        assert sum(out["counts"].values()) == len(out["sources"])
        assert all(
            src["status"] in {"published", "worked_out", "estimate", "your_choice"}
            for src in out["sources"]
        )


def test_each_source_says_what_it_is(client: TestClient, admin_headers: H) -> None:
    s = _estimate(client, admin_headers, ["online_forms", "ai_chatbot"])
    out = _sources(client, admin_headers, s["estimate_id"])
    by_kind: dict[str, list[Any]] = {}
    for src in out["sources"]:
        by_kind.setdefault(src["kind"], []).append(src)
    developer = next(r for r in by_kind["rate"] if r["title"] == "Developer day rate")
    assert developer["status"] == "published" and developer["url"].startswith("https://")
    assert developer["version"].startswith("rate card ")
    # a group of settings still marked placeholder says so; its values in this estimate shown
    guesses = [r for r in by_kind["setting"] if r["status"] == "estimate"]
    assert guesses and all(r["values"] for r in guesses)
    assert by_kind["hours"] and all(h["version"].startswith("catalog ") for h in by_kind["hours"])
    # the AI saving: each task's saving and the studies behind it, checked or not
    ai = by_kind["ai_saving"][0]
    assert any("saved" in v for v in ai["values"])
    assert any(c["checked"] for c in ai["cites"]) and any(not c["checked"] for c in ai["cites"])


def test_the_builders_profit_is_shown_to_everyone_with_its_source(
    client: TestClient, admin_headers: H, viewer_headers: H
) -> None:
    """OPEN_QUESTIONS 227: one profit for everyone, checked against published margins."""
    s = _estimate(client, admin_headers, ["online_forms"])
    seen = _sources(client, viewer_headers, s["estimate_id"])
    assert seen == _sources(client, admin_headers, s["estimate_id"])
    assert any(r["row"].startswith("item:commercial:margin") for r in seen["rows"])
    profit = next(src for src in seen["sources"] if src["kind"] == "margin")
    assert profit["status"] == "worked_out"
    assert profit["values"] == ["profit = 15% added on the cost"]
    assert len(profit["cites"]) >= 5 and all(c["url"] and c["checked"] for c in profit["cites"])


def test_the_reports_carry_the_sources(client: TestClient, admin_headers: H) -> None:
    s = _estimate(client, admin_headers, ["online_forms"])
    boq = client.get(f"/estimates/{s['estimate_id']}/boq.xlsx", headers=admin_headers)
    assert boq.status_code == 200
    wb = openpyxl.load_workbook(io.BytesIO(boq.content))
    sheet = wb["Sources"]
    assert [c.value for c in sheet[1]][:4] == ["#", "Source", "What it is", "Status"]
    assert sheet.max_row > 5
    inside = wb["Inside the price"]
    assert inside.cell(row=1, column=7).value == "Sources"
    assert str(inside.cell(row=2, column=7).value).startswith("[")
    pdf = client.get(f"/estimates/{s['estimate_id']}/report.pdf", headers=admin_headers)
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")


def test_prices_have_plain_names() -> None:
    cfg = quick_config()
    assert rate_title(cfg, "role.qa_engineer", "per_person_day") == "QA engineer day rate"
    assert rate_title(cfg, "licence.ssl_certificate_dv", "per_year") == "SSL certificate (a year)"
    assert rate_title(cfg, "forex.USD_INR", "inr_per_usd") == "Exchange rate (rupees per dollar)"

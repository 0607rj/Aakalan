"""OPEN_QUESTIONS 241: compare quotes. Quotes typed in for a project are each placed against the
estimate's own range before tax (below / in / above, % from the likely); they are kept per
project, reach the PDF and Excel, and change no price. The feature list to send out for quotes
carries no price of ours."""

import io
from typing import Any

import openpyxl
from fastapi.testclient import TestClient

H = dict[str, str]


def _estimate(client: TestClient, headers: H) -> Any:
    r = client.post(
        "/quick-estimates",
        json={
            "name": "Quotes test",
            "features": ["online_forms", "payments"],
            "choices": {"support_years": 2},
        },
        headers=headers,
    )
    assert r.status_code == 201, r.text
    return r.json()


def _put(client: TestClient, headers: H, estimate_id: str, quotes: list[dict[str, Any]]) -> Any:
    return client.put(f"/estimates/{estimate_id}/quotes", json={"quotes": quotes}, headers=headers)


def test_each_quote_is_placed_against_the_range(client: TestClient, admin_headers: H) -> None:
    s = _estimate(client, admin_headers)
    empty = client.get(f"/estimates/{s['estimate_id']}/quotes", headers=admin_headers).json()
    assert empty["quotes"] == [] and empty["currency"] == "INR"
    ranges = {r["covers"]: r for r in empty["ranges"]}
    whole = ranges["all"]
    # before tax: the likely is the summary's likely without GST, low and high lose the same share
    assert whole["likely_paise"] == s["likely_without_tax_paise"]
    assert whole["low_paise"] < whole["likely_paise"] < whole["high_paise"] < s["high_paise"]
    build = ranges["build"]
    assert build["likely_paise"] == s["quote_build_paise"] < whole["likely_paise"]

    r = _put(
        client,
        admin_headers,
        s["estimate_id"],
        [
            {"name": "  Low  Co ", "amount_paise": whole["low_paise"] - 100},
            {"name": "Fair", "amount_paise": whole["likely_paise"]},
            {"name": "High", "amount_paise": whole["high_paise"] + 100},
            {"name": "Build only", "amount_paise": build["likely_paise"], "covers": "build"},
        ],
    )
    assert r.status_code == 200, r.text
    quotes = r.json()["quotes"]
    assert [q["name"] for q in quotes] == ["Low Co", "Fair", "High", "Build only"]
    assert [q["verdict"] for q in quotes] == ["below", "in", "above", "in"]
    assert quotes[0]["versus_likely_percent"] < 0 < quotes[2]["versus_likely_percent"]
    assert quotes[1]["versus_likely_percent"] == 0 == quotes[3]["versus_likely_percent"]


def test_quotes_are_kept_per_project_and_replaced(client: TestClient, admin_headers: H) -> None:
    s = _estimate(client, admin_headers)
    _put(client, admin_headers, s["estimate_id"], [{"name": "A", "amount_paise": 500_00000}])
    new = client.post(f"/estimates/{s['estimate_id']}/reprice", headers=admin_headers)
    assert new.status_code == 201, new.text
    seen = client.get(f"/estimates/{new.json()['id']}/quotes", headers=admin_headers).json()
    assert [q["name"] for q in seen["quotes"]] == ["A"]  # a new version compares the same quotes
    r = _put(client, admin_headers, s["estimate_id"], [])
    assert r.json()["quotes"] == []


def test_viewers_see_quotes_but_cannot_change_them(
    client: TestClient, admin_headers: H, viewer_headers: H
) -> None:
    s = _estimate(client, admin_headers)
    _put(client, admin_headers, s["estimate_id"], [{"name": "A", "amount_paise": 100_00000}])
    seen = client.get(f"/estimates/{s['estimate_id']}/quotes", headers=viewer_headers)
    assert seen.status_code == 200 and len(seen.json()["quotes"]) == 1
    assert _put(client, viewer_headers, s["estimate_id"], []).status_code == 403


def test_bad_quotes_are_refused(client: TestClient, admin_headers: H) -> None:
    s = _estimate(client, admin_headers)
    for bad in (
        [{"name": "  ", "amount_paise": 100}],
        [{"name": "A", "amount_paise": 0}],
        [{"name": "A", "amount_paise": 100, "covers": "hosting"}],
        [{"name": f"Q{i}", "amount_paise": 100} for i in range(21)],
    ):
        assert _put(client, admin_headers, s["estimate_id"], bad).status_code == 422
    assert client.get("/estimates/not-an-id/quotes", headers=admin_headers).status_code == 404


def test_quotes_reach_the_pdf_and_excel(client: TestClient, admin_headers: H) -> None:
    s = _estimate(client, admin_headers)
    _put(client, admin_headers, s["estimate_id"], [{"name": "Vendor X", "amount_paise": 1_00}])
    xlsx = client.get(f"/estimates/{s['estimate_id']}/boq.xlsx", headers=admin_headers)
    assert xlsx.status_code == 200, xlsx.text
    wb = openpyxl.load_workbook(io.BytesIO(xlsx.content))
    sheet = wb["Quotes compared"]
    assert sheet["A2"].value == "Vendor X"
    assert str(sheet["E2"].value).startswith("Below the range")
    pdf = client.get(f"/estimates/{s['estimate_id']}/report.pdf", headers=admin_headers)
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")


def test_the_feature_list_for_quotes_has_no_prices(client: TestClient, admin_headers: H) -> None:
    s = _estimate(client, admin_headers)
    r = client.get(f"/estimates/{s['estimate_id']}/quote-form.xlsx", headers=admin_headers)
    assert r.status_code == 200, r.text
    assert "items-to-quote.xlsx" in r.headers["content-disposition"]
    ws = openpyxl.load_workbook(io.BytesIO(r.content))["Items to price"]
    rows = [[c.value for c in row] for row in ws.iter_rows()]
    items = [row[1] for row in rows if isinstance(row[0], int)]
    for feature in s["feature_costs"]:
        assert feature["label"] in items
    # the price column is empty for every item, and only formulas fill the totals
    assert all(row[3] is None for row in rows if isinstance(row[0], int))
    numbers = {v for row in rows for v in row if isinstance(v, int | float)}
    assert numbers <= set(range(1, len(items) + 1))  # item numbers only, no amount of ours
    assert any(isinstance(row[3], str) and row[3].startswith("=SUM(") for row in rows)

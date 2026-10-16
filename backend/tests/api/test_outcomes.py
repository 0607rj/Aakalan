"""Learn from results: record outcomes and compare them with the estimates."""

from fastapi.testclient import TestClient

H = dict[str, str]


def _estimate(client: TestClient, headers: H, name: str) -> dict[str, object]:
    body = {"name": name, "features": ["online_forms", "approval_workflow"]}
    s: dict[str, object] = client.post("/quick-estimates", json=body, headers=headers).json()
    return s


def test_record_outcome_and_calibration(client: TestClient, admin_headers: H) -> None:
    s = _estimate(client, admin_headers, "Outcome portal")
    p50 = s["likely_paise"]
    assert isinstance(p50, int)
    url = f"/projects/{s['project_id']}/outcome"
    assert client.get(url, headers=admin_headers).json() is None
    body = {"bid_result": "lost", "our_price_paise": p50, "l1_price_paise": p50 * 9 // 10}
    r = client.post(url, json=body, headers=admin_headers)
    assert r.status_code == 200, r.text
    assert r.json()["estimate_id"] == s["estimate_id"]  # defaults to the latest estimate
    # recording again replaces, not duplicates
    client.post(url, json={**body, "notes": "L1 was a local firm"}, headers=admin_headers)
    assert client.get(url, headers=admin_headers).json()["notes"] == "L1 was a local firm"

    report = client.get("/calibration", headers=admin_headers).json()
    row = next(x for x in report["rows"] if x["project_id"] == s["project_id"])
    assert row["l1_vs_estimate_percent"] == "-10.0"
    assert row["bid_result"] == "lost"
    assert report["with_l1"] >= 1 and "below our most-likely estimate" in report["message"]


def test_outcome_validation(client: TestClient, admin_headers: H, viewer_headers: H) -> None:
    s = _estimate(client, admin_headers, "Outcome validation")
    url = f"/projects/{s['project_id']}/outcome"
    assert client.post(url, json={"bid_result": "maybe"}, headers=admin_headers).status_code == 422
    neg = {"bid_result": "won", "l1_price_paise": -1}
    assert client.post(url, json=neg, headers=admin_headers).status_code == 422
    assert client.post(url, json={"bid_result": "won"}, headers=viewer_headers).status_code == 403
    assert (
        client.post(
            "/projects/nope/outcome", json={"bid_result": "won"}, headers=admin_headers
        ).status_code
        == 404
    )

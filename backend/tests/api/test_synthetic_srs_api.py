"""The five synthetic SRS documents end to end through the API, without an API key: uploaded
as DOCX (keyword reader), reviewed as the form would send them, and priced. Checks behaviour,
not real-world accuracy."""

from pathlib import Path
from typing import Any

import pytest
import yaml
from fastapi.testclient import TestClient

from app.llm.client import set_llm_client
from tests.api.test_documents import make_docx, upload

H = dict[str, str]
SRS = Path(__file__).parents[1] / "fixtures" / "srs"
MANIFESTS = sorted(p.name for p in SRS.glob("*.expected.yaml"))


def manifest(name: str) -> dict[str, Any]:
    data: dict[str, Any] = yaml.safe_load((SRS / name).read_text(encoding="utf-8"))
    return data


def docx_of(md: str) -> bytes:
    text = (SRS / md).read_text(encoding="utf-8")
    return make_docx(
        [[ln for ln in page.splitlines() if ln.strip()] for page in text.split("<!-- page -->")]
    )


def lines_of(client: TestClient, headers: H, estimate_id: str) -> list[tuple[Any, ...]]:
    detail = client.get(f"/estimates/{estimate_id}", headers=headers).json()
    return sorted(
        (ln["bucket"], ln["label"], ln["year"], ln["likely_paise"]) for ln in detail["lines"]
    )


@pytest.mark.parametrize("name", MANIFESTS)
def test_srs_upload_review_and_price(client: TestClient, admin_headers: H, name: str) -> None:
    set_llm_client(None)  # no key: the keyword reader
    m = manifest(name)
    doc = upload(
        client, admin_headers, m["document"].replace(".md", ".docx"), docx_of(m["document"])
    )
    assert doc.status_code == 201, doc.text
    body = doc.json()
    ex = body["extraction"]
    assert ex["reader"] == "basic"
    offered = {s["key"] for s in ex["scope"]}
    expected = {r["key"] for r in m["requirements"] if r["kind"] == "scope" and r["offered"]}
    # an item whose sentence already prices a ticked feature is not offered again
    may_drop = {
        r["key"]
        for r in m["requirements"]
        if r["kind"] == "scope" and r.get("pricing") == "already_included"
    }
    assert expected - may_drop <= offered <= expected
    for r in m["requirements"]:
        if r["kind"] == "scope" and not r["offered"]:
            assert r["key"] not in offered, r["id"]
    assert set(m["not_priced"]) <= {n["topic"] for n in ex["not_priced"]}

    form = {"name": m["project"], "features": m["features"]}
    # suggested but not ticked: priced exactly like the same form typed in by hand
    from_doc = client.post(
        "/quick-estimates", json={**form, "document_id": body["id"]}, headers=admin_headers
    ).json()
    by_hand = client.post("/quick-estimates", json=form, headers=admin_headers).json()
    assert from_doc["scope_items"] == [] and from_doc["planned_paise"] == by_hand["planned_paise"]
    assert lines_of(client, admin_headers, from_doc["estimate_id"]) == lines_of(
        client, admin_headers, by_hand["estimate_id"]
    )

    # every suggestion confirmed: each item's added cost follows the manifest
    confirmed = client.post(
        "/quick-estimates",
        json={**form, "document_id": body["id"], "scope": sorted(offered)},
        headers=admin_headers,
    ).json()
    items = {i["key"]: i for i in confirmed["scope_items"]}
    for r in m["requirements"]:
        if r["kind"] != "scope" or not r["offered"] or r["key"] not in offered:
            continue
        item = items[r["key"]]
        assert (item["amount_paise"] > 0) == (r["pricing"] == "adds_work"), r["id"]
        assert item["partly_priced"] == bool(r.get("partly_priced")), r["id"]
    adds = any(r.get("pricing") == "adds_work" for r in m["requirements"])
    assert (confirmed["planned_paise"] > by_hand["planned_paise"]) == adds
    assert confirmed["market"] == by_hand["market"]  # published prices: never moved by scope

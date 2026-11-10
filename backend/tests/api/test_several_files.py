"""OPEN_QUESTIONS 225: one project, several files (main document, annexures, an update,
answers to questions), each read on its own and merged; the same file is read once; at most
`project_max_documents` files; the independent check counts every file."""

from typing import Any

from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.services.extraction.merge import merged_inventory
from app.services.extraction.tender import FoundInventory, FoundItem, TenderExtraction
from tests.api.test_documents import TENDER_PAGES, make_pdf, no_override, upload

__all__ = ["no_override"]  # the fixture, used by name below

H = dict[str, str]

ANNEXURE = [
    [
        "Annexure B: Additional Requirements",
        "B.1 The portal shall provide an AI chatbot to answer vendor queries in English and Hindi.",
    ]
]
MAIN = [TENDER_PAGES[0], [line for line in TENDER_PAGES[1] if "chatbot" not in line]]


def add(client: TestClient, headers: H, project_id: str, name: str, data: bytes, kind: str) -> Any:
    return client.post(
        "/documents",
        files={"file": (name, data)},
        data={"project_id": project_id, "kind": kind},
        headers=headers,
    )


def test_an_annexure_adds_its_features_to_the_form(
    client: TestClient, admin_headers: H, no_override: None
) -> None:
    main = upload(client, admin_headers, "rfp.pdf", make_pdf(MAIN)).json()
    before = {f["key"] for f in main["extraction"]["features"]}
    assert "ai_chatbot" not in before
    pid = main["project_id"]
    r = add(client, admin_headers, pid, "annexure-b.pdf", make_pdf(ANNEXURE), "annexure")
    assert r.status_code == 201, r.text
    doc = client.get(f"/documents/{main['id']}", headers=admin_headers).json()
    assert [(f["filename"], f["kind"]) for f in doc["files"]] == [
        ("rfp.pdf", "rfp"),
        ("annexure-b.pdf", "annexure"),
    ]
    chatbot = next(f for f in doc["extraction"]["features"] if f["key"] == "ai_chatbot")
    assert chatbot["evidence"][0]["document"] == "annexure-b.pdf"
    form = client.get(f"/documents/{main['id']}/form", headers=admin_headers).json()
    assert "ai_chatbot" in form["request"]["features"]


def test_the_same_file_twice_is_read_once(
    client: TestClient, admin_headers: H, no_override: None
) -> None:
    data = make_pdf(MAIN)
    main = upload(client, admin_headers, "rfp.pdf", data).json()
    again = add(client, admin_headers, main["project_id"], "rfp copy.pdf", data, "annexure")
    assert again.status_code == 201 and again.json()["id"] == main["id"]
    doc = client.get(f"/documents/{main['id']}", headers=admin_headers).json()
    assert len(doc["files"]) == 1


def test_at_most_the_set_number_of_files(
    client: TestClient, admin_headers: H, no_override: None
) -> None:
    main = upload(client, admin_headers, "rfp.pdf", make_pdf(MAIN)).json()
    limit = get_settings().project_max_documents
    for i in range(1, limit):
        page = [[f"Annexure {i}", f"{i}.1 The portal shall send email notifications {i}."]]
        r = add(client, admin_headers, main["project_id"], f"a{i}.pdf", make_pdf(page), "annexure")
        assert r.status_code == 201, r.text
    over = add(client, admin_headers, main["project_id"], "x.pdf", make_pdf(ANNEXURE), "annexure")
    assert over.status_code == 422 and str(limit) in over.json()["detail"]


def _reading(reader: str, inventory: FoundInventory | None) -> TenderExtraction:
    return TenderExtraction(
        reader=reader,
        prompt_version="v",
        project_name="P",
        summary="",
        features=[],
        choices={},
        numbers={},
        unclear_points=[],
        dropped_findings=0,
        inventory=inventory,
    )


def _item(name: str, page: int) -> FoundItem:
    return FoundItem(name=name, evidence=[{"page": page, "clause_ref": "", "quote": name}])  # type: ignore[list-item]


def test_the_independent_check_counts_every_file() -> None:
    a = FoundInventory(prompt_version="v", entities=[_item("Vendor", 1), _item("Bill", 2)])
    b = FoundInventory(
        prompt_version="v",
        entities=[_item("vendor", 3), _item("Tender", 4)],
        tenancy="multi",
        system_class="workflow",
    )
    out = merged_inventory([_reading("ai", a), _reading("ai", b)])
    assert out is not None
    assert [e.name for e in out.entities] == ["Vendor", "Bill", "Tender"]  # vendor once
    assert [ev.page for ev in out.entities[0].evidence] == [1, 3]
    assert out.tenancy == "multi" and out.system_class == "workflow"
    # a file the AI read but could not count: no check, a person looks before export
    assert merged_inventory([_reading("ai", a), _reading("ai", None)]) is None
    assert merged_inventory([_reading("ai", a), _reading("basic", None)]) is not None

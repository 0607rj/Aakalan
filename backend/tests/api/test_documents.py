# ruff: noqa: E501  (inline fixture data)
"""Tender upload: parse (PDF/DOCX), read (basic reader without a key, or AI via a fake client),
verify every citation, then price the confirmed form with page-level traceability."""

import io
from collections.abc import Iterator
from typing import Any

import docx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.llm.client import FakeClient, set_llm_client
from app.models import Organisation, Role, User
from tests.conftest import TEST_PASSWORD, login

H = dict[str, str]

TENDER_PAGES = [
    [
        "Request for Proposal for Online Vendor Empanelment Portal",
        "Issued by Demo Public Sector Undertaking",
        "2.4 The Earnest Money Deposit (EMD) of Rs. 5,00,000 shall be submitted with the bid.",
        "2.6 The bidder shall furnish a Performance Bank Guarantee of 3% of the contract value.",
        "2.9 Go-live shall be achieved within 6 months of the issue of work order.",
    ],
    [
        "4.1 Vendors shall submit an online application with supporting documents.",
        "4.2 Applications shall pass a multi-level approval workflow with SLA tracking.",
        "4.3 Fees shall be paid through the payment gateway of the PSU.",
        "4.4 An AI chatbot shall answer vendor queries in English and Hindi.",
        "5.1 The portal will serve 50,000 registered users with 500 concurrent users at peak.",
        "5.2 The system shall be hosted on a MeitY empanelled cloud with 99.9% availability.",
        "8.1 The bidder shall provide 3 years of operations and maintenance after go-live.",
        "8.4 Training shall be provided to officials as per requirement.",
    ],
]


def make_docx(pages: list[list[str]]) -> bytes:
    document = docx.Document()
    for page in pages:
        for line in page:
            document.add_paragraph(line)
    buf = io.BytesIO()
    document.save(buf)
    return buf.getvalue()


def make_pdf(pages: list[list[str]]) -> bytes:
    """A minimal, valid text PDF (Helvetica, one line per row) — no PDF library needed."""
    objects: list[bytes] = []
    n_pages = len(pages)
    page_ids = [3 + 2 * i for i in range(n_pages)]
    font_id = 3 + 2 * n_pages
    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    kids = " ".join(f"{pid} 0 R" for pid in page_ids).encode()
    objects.append(
        b"<< /Type /Pages /Kids [" + kids + b"] /Count " + str(n_pages).encode() + b" >>"
    )
    for i, lines in enumerate(pages):
        content = (
            "BT /F1 9 Tf 40 800 Td 12 TL "
            + " ".join(
                "(" + ln.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)") + ") '"
                for ln in lines
            )
            + " ET"
        )
        stream = content.encode("latin-1")
        objects.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents {page_ids[i] + 1} 0 R "
            f"/Resources << /Font << /F1 {font_id} 0 R >> >> >>".encode()
        )
        objects.append(
            b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream"
        )
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    out = io.BytesIO()
    out.write(b"%PDF-1.4\n")
    offsets = []
    for num, body in enumerate(objects, start=1):
        offsets.append(out.tell())
        out.write(f"{num} 0 obj\n".encode() + body + b"\nendobj\n")
    xref = out.tell()
    out.write(f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode())
    for off in offsets:
        out.write(f"{off:010d} 00000 n \n".encode())
    out.write(
        f"trailer << /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF".encode()
    )
    return out.getvalue()


def upload(client: TestClient, headers: H, name: str, data: bytes) -> Any:
    return client.post("/documents", files={"file": (name, data)}, headers=headers)


@pytest.fixture
def no_override() -> Iterator[None]:
    set_llm_client(None)
    yield
    set_llm_client(None)


def test_basic_reader_without_a_key(
    client: TestClient, admin_headers: H, no_override: None
) -> None:
    r = upload(client, admin_headers, "tender.pdf", make_pdf(TENDER_PAGES))
    assert r.status_code == 201, r.text
    doc = r.json()
    assert doc["status"] == "extracted" and doc["pages"] == 2 and not doc["approximate_pages"]
    ex = doc["extraction"]
    assert ex["reader"] == "basic"
    keys = {f["key"] for f in ex["features"]}
    assert {"online_forms", "approval_workflow", "payments", "ai_chatbot", "languages"} <= keys
    pay = next(f for f in ex["features"] if f["key"] == "payments")
    assert pay["evidence"][0] == {
        "page": 2,
        "clause_ref": "4.3",
        "quote": "4.3 Fees shall be paid through the payment gateway of the PSU.",
        "document": "tender.pdf",
        "checked": True,
    }
    n = ex["numbers"]
    assert n["om_years"]["value"] == 3 and n["deadline_months"]["value"] == 6
    assert n["users_total"]["value"] == 50000 and n["peak_concurrent_users"]["value"] == 500
    assert n["emd_paise"]["value"] == 50_000_000 and n["pbg_percent"]["value"] == 0.03
    c = ex["choices"]
    assert c["availability"]["value"] == "high" and c["hosting"]["value"] == "indian_cloud"
    assert c["scale"]["value"] == "medium"
    assert doc["project_name"].startswith("Request for Proposal")


def test_docx_upload_has_approximate_pages(
    client: TestClient, admin_headers: H, no_override: None
) -> None:
    doc = upload(client, admin_headers, "tender.docx", make_docx(TENDER_PAGES)).json()
    assert doc["file_type"] == "docx" and doc["approximate_pages"]
    assert {f["key"] for f in doc["extraction"]["features"]} >= {"payments", "ai_chatbot"}


def test_ai_reader_citations_are_verified(client: TestClient, admin_headers: H) -> None:
    """The AI path: invented quotes and unknown keys are dropped, real ones are kept."""

    def responder(system: str, user: str) -> object:
        assert "<tender_document>" in user and 'page number="2"' in user
        assert "Never estimate" in system  # rule 1 is in the prompt
        return {
            "project_name": "Online Vendor Empanelment Portal",
            "summary": "A portal for vendors to apply online.",
            "features": [
                {"key": "payments", "evidence": [{"page": 2, "clause_ref": "4.3", "quote": "Fees shall be paid through the payment gateway"}]},
                {"key": "aadhaar_digilocker", "evidence": [{"page": 2, "clause_ref": "4.9", "quote": "Citizens shall log in with Aadhaar"}]},
                {"key": "teleport", "evidence": [{"page": 1, "clause_ref": "", "quote": "Request for Proposal for Online"}]},
            ],
            "choices": [{"question": "support_hours", "value": "always", "evidence": [{"page": 2, "clause_ref": "5.2", "quote": "99.9% availability"}]}],
            "numbers": [{"field": "om_years", "value": 3, "evidence": [{"page": 2, "clause_ref": "8.1", "quote": "3 years of operations and maintenance"}]}],
            "unclear_points": [{"topic": "Helpdesk hours", "why": "Not stated", "page": None, "clause_ref": "", "quote": "", "prebid_query": "Kindly confirm the helpdesk support hours."}],
        }  # fmt: skip

    set_llm_client(FakeClient(responder))
    try:
        doc = upload(client, admin_headers, "tender.pdf", make_pdf(TENDER_PAGES)).json()
    finally:
        set_llm_client(None)
    ex = doc["extraction"]
    assert ex["reader"] == "ai" and doc["llm_model"] == "fake"
    assert [f["key"] for f in ex["features"]] == ["payments"]  # invented quote + bad key dropped
    assert ex["choices"]["support_hours"]["value"] == "always"  # quote is real, user will review
    assert ex["numbers"]["om_years"]["value"] == 3
    assert ex["dropped_findings"] == 2
    assert ex["unclear_points"][0]["topic"] == "Helpdesk hours"


def test_estimate_from_document_traces_to_pages(
    client: TestClient, admin_headers: H, no_override: None
) -> None:
    doc = upload(client, admin_headers, "tender.pdf", make_pdf(TENDER_PAGES)).json()
    ex = doc["extraction"]
    body = {
        "name": "Vendor empanelment portal",
        "document_id": doc["id"],
        "features": [f["key"] for f in ex["features"]],
        "choices": {k: v["value"] for k, v in ex["choices"].items() if k != "support_years"},
        "overrides": {k: v["value"] for k, v in ex["numbers"].items()},
    }
    s = client.post("/quick-estimates", json=body, headers=admin_headers)
    assert s.status_code == 201, s.text
    summary = s.json()
    assert summary["project_id"] == doc["project_id"] and summary["support_years"] == 3
    detail = client.get(f"/estimates/{summary['estimate_id']}", headers=admin_headers).json()
    assert detail["timeline"]["deadline_months"] == "6"
    traces = [
        client.get(
            f"/estimates/{summary['estimate_id']}/lines/{ln['id']}/trace", headers=admin_headers
        ).json()["trace"]
        for ln in detail["lines"]
        if ln["bucket"] == "build.integrations"
    ]
    payment = next(
        t for t in traces if t["component"]["catalog_key"] == "integration_payment_gateway"
    )
    pages = {(r["clause_ref"], r["page"]) for r in payment["requirements"]}
    assert ("4.3", 2) in pages  # payment gateway -> RFP clause 4.3 on page 2
    emd = next(ln for ln in detail["lines"] if ln["bucket"] == "commercial.emd")
    emd_trace = client.get(
        f"/estimates/{summary['estimate_id']}/lines/{emd['id']}/trace", headers=admin_headers
    ).json()["trace"]
    assert any(r["clause_ref"] == "2.4" and r["page"] == 1 for r in emd_trace["requirements"])
    # recalculating from the same upload replaces the mapping instead of duplicating it
    again = client.post("/quick-estimates", json=body, headers=admin_headers).json()
    assert (
        again["project_id"] == doc["project_id"]
        and again["planned_paise"] == summary["planned_paise"]
    )


def test_prebid_queries(client: TestClient, admin_headers: H, no_override: None) -> None:
    doc = upload(client, admin_headers, "tender.pdf", make_pdf(TENDER_PAGES)).json()
    r = client.get(f"/documents/{doc['id']}/prebid-queries", headers=admin_headers)
    assert r.status_code == 200
    queries = r.json()
    vague = [q for q in queries if q["kind"] == "unclear"]
    assert vague and vague[0]["clause_ref"] == "8.4" and vague[0]["page"] == 2
    assert "8.4" in vague[0]["query"] and "as per requirement" in vague[0]["quote"]
    missing = {q["topic"] for q in queries if q["kind"] == "missing"}
    assert "Support hours not stated" in missing  # tender never says office hours or 24x7
    assert "Om years not stated" not in missing  # stated in clause 8.1
    assert [q["number"] for q in queries] == list(range(1, len(queries) + 1))


@pytest.mark.parametrize(
    ("name", "data", "message"),
    [
        ("notes.txt", b"hello", "PDF or a Word"),
        ("fake.pdf", b"not a pdf at all", "PDF or a Word"),
        ("blank.pdf", make_pdf([[" "]]), "scanned"),
    ],
)
def test_bad_files_get_clear_messages(
    client: TestClient, admin_headers: H, name: str, data: bytes, message: str
) -> None:
    r = upload(client, admin_headers, name, data)
    assert r.status_code == 400 and message in r.json()["detail"]


def test_upload_is_org_scoped(
    client: TestClient, admin_headers: H, db: Session, no_override: None
) -> None:
    doc = upload(client, admin_headers, "tender.pdf", make_pdf(TENDER_PAGES)).json()
    other = Organisation(name="Other SI (documents)")
    db.add(other)
    db.flush()
    db.add(
        User(
            org_id=other.id,
            email="docs-spy@other.local",
            full_name="Spy",
            role=Role.ADMIN,
            password_hash=hash_password(TEST_PASSWORD),
        )
    )
    db.commit()
    spy = login(client, "docs-spy@other.local")
    assert client.get(f"/documents/{doc['id']}", headers=spy).status_code == 404
    assert client.get(f"/documents/{doc['id']}", headers=admin_headers).status_code == 200


def test_corrigendum_overrides_rfp(client: TestClient, admin_headers: H, no_override: None) -> None:
    rfp = upload(client, admin_headers, "rfp.pdf", make_pdf(TENDER_PAGES)).json()
    corr_pages = [
        [
            "Corrigendum No. 1",
            "2.9 Go-live shall be achieved within 4 months of the issue of work order.",
        ]
    ]
    r = client.post(
        "/documents",
        files={"file": ("corrigendum-1.pdf", make_pdf(corr_pages))},
        data={"project_id": rfp["project_id"], "kind": "corrigendum"},
        headers=admin_headers,
    )
    assert r.status_code == 201, r.text
    assert r.json()["project_id"] == rfp["project_id"]
    assert r.json()["project_name"] == rfp["project_name"]  # first document names the project
    merged = client.get(f"/projects/{rfp['project_id']}/extraction", headers=admin_headers).json()
    assert [d["kind"] for d in merged["documents"]] == ["rfp", "corrigendum"]
    assert merged["extraction"]["numbers"]["deadline_months"]["value"] == 4
    assert merged["changes"] == [
        {
            "field": "deadline_months",
            "old_value": 6,
            "new_value": 4,
            "document": "corrigendum-1.pdf",
            "kind": "corrigendum",
        }
    ]
    ex = merged["extraction"]
    body = {
        "name": "Portal",
        "document_id": rfp["id"],
        "features": [f["key"] for f in ex["features"]],
        "overrides": {"deadline_months": 4},
    }
    s = client.post("/quick-estimates", json=body, headers=admin_headers).json()
    detail = client.get(f"/estimates/{s['estimate_id']}", headers=admin_headers).json()
    assert detail["timeline"]["deadline_months"] == "4"
    pm = next(ln for ln in detail["lines"] if ln["line_key"] == "programme.project_management/pm")
    trace = client.get(
        f"/estimates/{s['estimate_id']}/lines/{pm['id']}/trace", headers=admin_headers
    ).json()["trace"]
    deadline = next(d for d in trace["drivers"] if d["key"] == "deadline_months")
    assert deadline["value"] == "4" and deadline["requirement_ids"]
    cited = [r for r in trace["requirements"] if r["id"] in deadline["requirement_ids"]]
    assert cited and cited[0]["clause_ref"] == "2.9"


def test_unknown_document_kind_rejected(client: TestClient, admin_headers: H) -> None:
    r = client.post(
        "/documents",
        files={"file": ("x.pdf", make_pdf(TENDER_PAGES))},
        data={"kind": "love-letter"},
        headers=admin_headers,
    )
    assert r.status_code == 422


def test_scanned_pdf_read_by_ai_with_unchecked_quotes(client: TestClient, admin_headers: H) -> None:
    seen: dict[str, str] = {}

    def responder(system: str, user: str) -> object:
        seen["user"] = user
        return {
            "project_name": "Scanned tender",
            "summary": "A scanned RFP.",
            "features": [{"key": "payments", "evidence": [{"page": 1, "clause_ref": "3.2", "quote": "Payment through gateway of the department"}]}],
            "choices": [],
            "numbers": [{"field": "om_years", "value": 2, "evidence": [{"page": 9, "clause_ref": "", "quote": "two years of O&M after go-live"}]}],
            "unclear_points": [],
        }  # fmt: skip

    set_llm_client(FakeClient(responder))
    try:
        r = upload(client, admin_headers, "scanned.pdf", make_pdf([[" "], [" "]]))
    finally:
        set_llm_client(None)
    assert r.status_code == 201, r.text
    assert seen["user"].startswith("[PDF ")  # sent as a PDF, not as extracted text
    ex = r.json()["extraction"]
    assert ex["features"][0]["evidence"][0]["checked"] is False
    assert ex["numbers"] == {}  # page 9 does not exist in a 2-page document -> dropped

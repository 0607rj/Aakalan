"""A scanned PDF gets the second "what did the first reading miss" pass too (OPEN_QUESTIONS 203):
sent again as the PDF, with what was already found, and its extras added."""

from app.llm.client import FakeClient
from app.services.documents.parsing import Page, ParsedDocument
from app.services.extraction.tender import ai_read
from app.services.quick.config import quick_config

FIRST = {
    "project_name": "Scanned tender",
    "summary": "A scanned RFP.",
    "features": [{"key": "payments", "evidence": [{"page": 1, "clause_ref": "", "quote": "pay"}]}],
    "other_features": [],
    "choices": [],
    "numbers": [],
    "unclear_points": [],
}
EXTRA = {
    "name": "Stall allotment",
    "description": "Allot stalls to exhibitors.",
    "category": "module",
    "size": "M",
    "evidence": [{"page": 2, "clause_ref": "", "quote": "allotment of stalls"}],
}


def test_a_scanned_pdf_is_asked_what_it_missed() -> None:
    calls: list[str] = []

    def responder(system: str, user: str) -> object:
        calls.append(user)
        if "<already_found>" in user:
            return {"other_features": [EXTRA]}
        return FIRST

    doc = ParsedDocument(
        kind="pdf", pages=[Page(1, ""), Page(2, "")], approximate_pages=False, scanned=True
    )
    result = ai_read(FakeClient(responder), quick_config(), doc, pdf=b"%PDF-1.4 scanned")
    assert len(calls) == 2 and all(c.startswith("[PDF ") for c in calls)  # both see the PDF
    assert "- payments" in calls[1]  # told what the first reading found
    assert [o.name for o in result.output.other_features] == ["Stall allotment"]
    assert [f.key for f in result.output.features] == ["payments"]

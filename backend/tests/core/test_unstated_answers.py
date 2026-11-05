"""A sentence saying the document does not state something answers nothing (OPEN_QUESTIONS
218): "The requirement document does not state the helpdesk support hours" left the helpdesk
at "yes" (an AI reading of an estimate report's pre-bid list). An answer whose every quote
says so, asks for it or is a question is dropped and the question keeps its usual answer."""

from types import SimpleNamespace
from typing import Any

from app.llm.client import FakeClient
from app.services.documents.parsing import Page, ParsedDocument
from app.services.extraction.merge import merge_extractions, unstated
from app.services.extraction.tender import TenderExtraction, ai_read, verify_findings
from app.services.quick.config import quick_config

CFG = quick_config()
NOT_STATED = "The requirement document does not state the helpdesk support hours."
STATED = "The bidder shall provide a helpdesk team to answer citizens' calls."


def _merged(text: str, quote: str) -> TenderExtraction:
    raw: Any = {
        "project_name": "Portal", "summary": "", "features": [], "other_features": [],
        "numbers": [], "unclear_points": [], "scope": [],
        "choices": [{"question": "helpdesk_scope", "value": "yes",
                     "evidence": [{"page": 1, "clause_ref": "", "quote": quote}]}],
    }  # fmt: skip
    doc = ParsedDocument(kind="pdf", pages=[Page(1, text)], approximate_pages=False)
    client = FakeClient(lambda s, u: {"other_features": []} if "<already_found>" in u else raw)
    ex = verify_findings(CFG, doc, ai_read(client, CFG, doc).output, reader="ai", version="t")
    stored = SimpleNamespace(
        kind="rfp",
        filename="rfp.pdf",
        page_texts=[{"page": 1, "text": text}],
        extraction={"reader": "ai"},
    )
    merged, _ = merge_extractions([(stored, ex)])  # type: ignore[list-item]
    return merged


def test_a_not_stated_sentence_gives_no_answer() -> None:
    merged = _merged(NOT_STATED, NOT_STATED)
    assert "helpdesk_scope" not in merged.choices


def test_a_stated_helpdesk_is_still_read() -> None:
    merged = _merged(STATED, STATED)
    assert merged.choices["helpdesk_scope"].value == "yes"


def test_which_sentences_answer_nothing() -> None:
    assert unstated(NOT_STATED)
    assert unstated("Kindly confirm the O&M period after go-live.")
    assert unstated("Please specify the hosting vendor, region and SLA expected.")
    assert unstated("The uptime has not been specified by the department.")
    assert unstated("Is migration of existing spreadsheet records required?")
    assert not unstated(STATED)
    assert not unstated("Support shall be provided 24x7 by a staffed helpdesk.")

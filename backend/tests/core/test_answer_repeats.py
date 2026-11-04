"""One sentence is priced once (OPEN_QUESTIONS 206): an extra that quotes only the sentence of
an answer that adds a feature (integrations "one or two" adds connect_existing) repeats it and
is dropped; an extra with a sentence of its own stays."""

from typing import Any

from app.llm.client import FakeClient
from app.services.documents.parsing import Page, ParsedDocument
from app.services.extraction.tender import ai_read, verify_findings
from app.services.quick.config import quick_config

CFG = quick_config()
BUREAU = "3.5 The system shall fetch the credit score from a credit bureau through its API."
NACH = "3.9 Applicants shall set up an e-NACH mandate so that EMIs are collected every month."


def _extra(name: str, quote: str) -> dict[str, Any]:
    return {
        "name": name, "description": name, "category": "integration", "size": "S",
        "evidence": [{"page": 1, "clause_ref": "", "quote": quote}],
    }  # fmt: skip


def test_an_extra_repeating_a_feature_adding_answer_is_dropped() -> None:
    raw = {
        "project_name": "Loans", "summary": "", "features": [], "numbers": [],
        "unclear_points": [], "scope": [],
        "choices": [{"question": "integrations", "value": "one_two",
                     "evidence": [{"page": 1, "clause_ref": "", "quote": BUREAU}]}],
        "other_features": [_extra("Credit bureau score fetch", BUREAU), _extra("e-NACH", NACH)],
    }  # fmt: skip
    doc = ParsedDocument(
        kind="text", pages=[Page(1, f"{BUREAU}\n{NACH}\n")], approximate_pages=False
    )
    client = FakeClient(lambda s, u: {"other_features": []} if "<already_found>" in u else raw)
    ex = verify_findings(CFG, doc, ai_read(client, CFG, doc).output, reader="ai", version="t")
    assert ex.choices["integrations"].value == "one_two"
    assert [o.name for o in ex.other_features] == ["e-NACH"]

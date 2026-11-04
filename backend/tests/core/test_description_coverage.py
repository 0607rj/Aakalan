"""A typed description: every part of it asks for something (OPEN_QUESTIONS 210). A part no
finding accounts for is listed as "not matched yet", so nothing is lost silently."""

from typing import Any

from app.llm.client import FakeClient
from app.services.documents.parsing import Page, ParsedDocument
from app.services.extraction.coverage import unmatched_parts
from app.services.extraction.tender import ai_read, verify_findings
from app.services.quick.config import quick_config

CFG = quick_config()
assert CFG.coverage is not None
COV = CFG.coverage
TEXT = "A system for my school where parents pay fees online and see their child's attendance."


def _read(features: list[dict[str, Any]], others: list[dict[str, Any]], text: str = TEXT) -> Any:
    raw = {
        "project_name": "", "summary": "", "project_domain": "School management",
        "features": features, "other_features": others, "choices": [], "numbers": [],
        "unclear_points": [],
    }  # fmt: skip
    doc = ParsedDocument(kind="text", pages=[Page(1, text)], approximate_pages=False)
    client = FakeClient(lambda s, u: {"other_features": []} if "<already_found>" in u else raw)
    return verify_findings(CFG, doc, ai_read(client, CFG, doc).output, reader="ai", version="t")


def _ev(quote: str) -> list[dict[str, Any]]:
    return [{"page": 1, "clause_ref": "", "quote": quote}]


ATTENDANCE = {
    "name": "Parent view of child attendance", "description": "Parents see attendance.",
    "category": "module", "size": "M", "evidence": _ev("see their child's attendance"),
}  # fmt: skip


def test_a_missed_ask_is_listed() -> None:
    ex = _read([{"key": "payments", "evidence": _ev("parents pay fees online")}], [])
    assert unmatched_parts(COV, ex, TEXT, []) == ["see their child's attendance"]


def test_one_quote_running_over_two_asks_is_one_finding_not_two() -> None:
    quote = "where parents pay fees online and see their child's attendance"
    ex = _read([{"key": "payments", "evidence": _ev(quote)}], [])
    assert unmatched_parts(COV, ex, TEXT, []) == ["see their child's attendance"]


def test_everything_found_lists_nothing_and_naming_the_software_asks_nothing() -> None:
    ex = _read([{"key": "payments", "evidence": _ev("parents pay fees online")}], [ATTENDANCE])
    assert unmatched_parts(COV, ex, TEXT, []) == []
    assert unmatched_parts(COV, ex, f"A school system. {TEXT}", []) == []


def test_a_ruled_out_clause_is_accounted_for() -> None:
    text = f"{TEXT} We do not need a mobile app."
    ex = _read([{"key": "payments", "evidence": _ev("parents pay fees online")}], [ATTENDANCE])
    assert unmatched_parts(COV, ex, text, []) == ["We do not need a mobile app"]
    assert unmatched_parts(COV, ex, text, ["We do not need a mobile app"]) == []

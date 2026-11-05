"""OPEN_QUESTIONS 221: a quote is checked word for word, skipping the row numbers a PDF table
mixes into a cell and line-break hyphens, so a real finding is not dropped; a wrong number in
the quote still fails."""

from typing import Any

from app.llm.client import FakeClient
from app.services.documents.parsing import Page, ParsedDocument, contains_quote, words_of
from app.services.extraction.tender import ai_read, verify_findings
from app.services.quick.config import quick_config

TABLE_CELL = (
    "Chatbot with Multilingual capability, including English and Hindi,\n31\nshould be provided."
)


def _found(page: str, quote: str) -> bool:
    return contains_quote(words_of(page), words_of(quote))


def test_a_row_number_inside_a_table_cell_is_skipped() -> None:
    assert _found(
        TABLE_CELL,
        "Chatbot with Multilingual capability, including English and Hindi, should be provided.",
    )


def test_a_line_break_hyphen_is_the_same_word() -> None:
    assert _found(
        "along with 3 years of maintenance post go-\nlive (as mentioned in clause no. 3.6).",
        "along with 3 years of maintenance post go-live",
    )


def test_a_wrong_number_or_other_words_still_fail() -> None:
    page = "along with 3 years of maintenance post go-live"
    assert not _found(page, "along with 5 years of maintenance post go-live")
    assert not _found("Chatbot with English 1 2 3 4 support", "Chatbot with English support")
    assert not _found(TABLE_CELL, "Chatbot with Multilingual capability, including Tamil")


def test_the_reading_keeps_a_feature_quoted_from_a_table_cell() -> None:
    cfg = quick_config()
    quote = "Chatbot with Multilingual capability, including English and Hindi, should be provided."
    raw: Any = {
        "project_name": "Portal", "summary": "", "other_features": [], "numbers": [],
        "unclear_points": [], "scope": [], "choices": [],
        "features": [{"key": "languages",
                      "evidence": [{"page": 1, "clause_ref": "", "quote": quote}]}],
    }  # fmt: skip
    doc = ParsedDocument(kind="pdf", pages=[Page(1, TABLE_CELL)], approximate_pages=False)
    client = FakeClient(lambda s, u: {"other_features": []} if "<already_found>" in u else raw)
    ex = verify_findings(cfg, doc, ai_read(client, cfg, doc).output, reader="ai", version="t")
    assert [f.key for f in ex.features] == ["languages"]
    assert ex.dropped_findings == 0

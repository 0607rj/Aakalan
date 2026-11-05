"""A PDF wraps sentences over lines (OPEN_QUESTIONS 216): the keyword reader judges the whole
sentence, so "No ... payment gateway ... has been selected", a list under "not included ...:"
and a question ("Is data migration required?") ask for nothing; plain section headings
("5. External Integrations") are clause numbers, carried over to the next page; and after an AI
reading the keywords add no feature (OPEN_QUESTIONS 217)."""

from types import SimpleNamespace
from typing import Any

from app.llm.client import FakeClient
from app.services.documents.parsing import Page, ParsedDocument
from app.services.extraction.basic_reader import basic_read
from app.services.extraction.merge import merge_extractions
from app.services.extraction.tender import ai_read, verify_findings
from app.services.quick.config import quick_config

CFG = quick_config()


def _read(*pages: str) -> Any:
    doc = ParsedDocument(
        kind="text",
        pages=[Page(i + 1, t) for i, t in enumerate(pages)],
        approximate_pages=False,
    )
    return basic_read(CFG, doc)


def _keys(*pages: str) -> set[str]:
    return {f.key for f in _read(*pages).features}


def test_a_provider_not_yet_selected_is_not_asked_for() -> None:
    page = (
        "5. External Integrations\n"
        "No external calendar integration, payment gateway, WhatsApp provider, SMS gateway, or\n"
        "third-party healthcare system has been selected. Do not assume all integrations\n"
        "are required.\n"
    )
    keys = _keys(page)
    assert "payments" not in keys
    assert "notifications" not in keys


def test_a_list_under_not_included_wrapped_over_lines_is_ruled_out() -> None:
    page = (
        "11. Explicit Exclusions\n"
        "The following are not included in the first release unless separately approved:\n"
        "native mobile applications, video calls, online payments, prescriptions and\n"
        "laboratory integrations.\n"
    )
    assert "payments" not in _keys(page)


def test_a_question_and_a_bare_heading_are_not_requirements() -> None:
    page = (
        "8. Data Migration\n"
        "The client may have existing patient records in spreadsheets. Do not assume a full\n"
        "historical migration is included.\n"
        "12. Open Questions\n"
        "1. Is historical patient data migration required? If yes, what is the volume?\n"
    )
    assert "old_data" not in _keys(page)


def test_a_wrapped_requirement_is_still_found_once_with_its_clause() -> None:
    page = (
        "4.6 Notifications and Reminders\n"
        "The system should send booking confirmations and appointment reminders to\n"
        "patients. The client has not yet selected the delivery channels.\n"
    )
    found = {f.key: f for f in _read(page).features}
    assert "notifications" in found
    evidence = found["notifications"].evidence
    assert len(evidence) == 1
    assert evidence[0].clause_ref == "4.6"


def test_plain_headings_are_clauses_and_carry_to_the_next_page() -> None:
    first = "4.2 Payments\nIntro text.\n9. Fees\nCitizens shall pay the fee online with\n"
    second = "a card or UPI through the payment gateway.\n"
    payments = {f.key: f for f in _read(first, second).features}["payments"]
    clauses = {(ev.page, ev.clause_ref) for ev in payments.evidence}
    assert (1, "9") in clauses
    assert (2, "9") in clauses


def test_a_numbered_question_is_not_a_clause_heading() -> None:
    page = "7.3 Open points\n1. Which channels are needed: SMS or email?\nUsers shall pay online.\n"
    payments = {f.key: f for f in _read(page).features}["payments"]
    assert payments.evidence[0].clause_ref == "7.3"


def test_after_an_ai_reading_keywords_add_no_feature() -> None:
    text = (
        "3.2 Customers shall pay online through a payment gateway when they order.\n"
        "3.3 Every order shall come with a GST invoice that the customer can download.\n"
    )
    raw = {
        "project_name": "Shop", "summary": "", "other_features": [], "choices": [],
        "numbers": [], "unclear_points": [], "scope": [],
        "features": [{"key": "payments", "evidence": [
            {"page": 1, "clause_ref": "3.2", "quote": "pay online through a payment gateway"}
        ]}],
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
    by_key = {f.key: f for f in merged.features}
    assert by_key["payments"].suggested  # the AI asked for it: ticked
    assert "billing" not in by_key  # only its words: not added

"""A feature the reader skips is never lost silently (OPEN_QUESTIONS 204): the keyword check
adds a listed feature an AI reading missed, every requirement sentence nothing quotes is
listed, and "sign in with Google" is the social login choice, not staff single sign-on."""

from types import SimpleNamespace
from typing import Any

from app.llm.client import FakeClient
from app.services.documents.parsing import Page, ParsedDocument
from app.services.extraction.coverage import find_uncovered, is_requirement
from app.services.extraction.merge import merge_extractions
from app.services.extraction.tender import TenderExtraction, ai_read, verify_findings
from app.services.quick.config import Coverage, quick_config

CFG = quick_config()
_COVERAGE = CFG.coverage
assert _COVERAGE is not None
COVERAGE: Coverage = _COVERAGE

PAGE = (
    "3.1 Candidates shall upload their resume and certificates as documents.\n"
    "3.2 Customers shall pay online through a payment gateway when they order.\n"
    "3.3 Every order shall come with a GST invoice that the customer can download.\n"
    "4.1 The bidder shall submit an EMD of Rs 50,000 with the bid.\n"
)


def reading(features: list[dict[str, Any]], scope: list[dict[str, Any]] | None = None) -> Any:
    return {
        "project_name": "Shop", "summary": "", "features": features, "other_features": [],
        "choices": [], "numbers": [], "unclear_points": [], "scope": scope or [],
    }  # fmt: skip


def ev(quote: str) -> list[dict[str, Any]]:
    return [{"page": 1, "clause_ref": "", "quote": quote}]


def read(raw: Any, text: str = PAGE, kind: str = "rfp") -> TenderExtraction:
    """An AI reading of one page, merged as the app merges a project's documents."""
    doc = ParsedDocument(kind="pdf", pages=[Page(1, text)], approximate_pages=False)
    client = FakeClient(lambda s, u: {"other_features": []} if "<already_found>" in u else raw)
    ex = verify_findings(CFG, doc, ai_read(client, CFG, doc).output, reader="ai", version="t")
    stored = SimpleNamespace(
        kind=kind,
        filename="rfp.pdf",
        page_texts=[{"page": 1, "text": text}],
        extraction={"reader": "ai"},
    )
    merged, _ = merge_extractions([(stored, ex)])  # type: ignore[list-item]
    return merged


def test_the_keyword_check_adds_what_the_ai_missed_and_says_so() -> None:
    merged = read(reading([{"key": "payments", "evidence": ev("pay online through a payment")}]))
    by_key = {f.key: f for f in merged.features}
    assert by_key["payments"].found_by == "reader"
    assert by_key["billing"].found_by == "keywords"  # "GST invoice", missed by the AI
    assert by_key["billing"].evidence[0].page == 1


def test_the_keyword_check_never_reads_a_corrigendum() -> None:
    merged = read(reading([]), kind="corrigendum")
    assert all(f.found_by == "reader" for f in merged.features)


def test_requirement_sentences_nothing_quotes_are_listed() -> None:
    quote = "Customers shall pay online through a payment gateway when they order."
    merged = read(reading([{"key": "payments", "evidence": ev(quote)}]))
    listed = [u.text for u in merged.uncovered]
    assert not any("payment gateway" in t for t in listed)  # quoted by a finding
    assert not any("bidder" in t for t in listed)  # the bidder's duty, not software
    assert merged.uncovered_more == 0


def test_a_short_quote_covers_its_sentence_and_the_list_is_stable() -> None:
    text = "5.2 Support shall be provided 24x7.\nUsers shall export reports to Excel."
    pages = [("a.pdf", [(1, text)])]
    nothing = read(reading([]), text="Nothing here.")
    first = find_uncovered(COVERAGE, nothing, pages)
    assert [u.text for u in first[0]] == [
        "5.2 Support shall be provided 24x7.",
        "Users shall export reports to Excel.",
    ]
    assert find_uncovered(COVERAGE, nothing, pages) == first  # the same every time
    # a 5-word quote of the first line covers it, though the line also has its clause number
    said = [{"key": "dashboards", "evidence": ev("Support shall be provided 24x7.")}]
    one = read(reading(said), text)
    assert [u.text for u in find_uncovered(COVERAGE, one, pages)[0]] == [
        "Users shall export reports to Excel."
    ]


def test_what_counts_as_a_requirement() -> None:
    assert is_requirement(COVERAGE, "Recruiters shall see MIS reports of applications per job.")
    assert not is_requirement(COVERAGE, "The bidder shall submit three similar work orders.")
    assert not is_requirement(COVERAGE, "Data is stored in India.")  # asks for nothing
    assert not is_requirement(COVERAGE, "Users shall log in.")  # too short to say what


def test_sign_in_with_google_is_social_login_not_staff_sign_on() -> None:
    quote = "Candidates shall be able to sign in with Google."
    raw = reading(
        [{"key": "staff_login", "evidence": ev(quote)}],
        [{"key": "social_login", "status": "explicit", "evidence": ev(quote)}],
    )
    merged = read(raw, text=quote)
    assert "staff_login" not in {f.key for f in merged.features}
    assert [s.key for s in merged.scope] == ["social_login"]


def test_staff_sign_on_with_its_own_sentence_stays() -> None:
    text = "Officers shall sign in through Parichay.\nCitizens shall sign in with Google."
    raw = reading(
        [{"key": "staff_login", "evidence": ev("Officers shall sign in through Parichay.")}],
        [{"key": "social_login", "status": "explicit", "evidence": ev("sign in with Google")}],
    )
    assert "staff_login" in {f.key for f in read(raw, text=text).features}

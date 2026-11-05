"""OPEN_QUESTIONS 220: a feature or extra the reading found only on a page of contract or bid
terms is offered, not ticked (never dropped); a scope page full of "The Bidder shall
provide..." is still a scope page; registering with a mobile number is a feature, not contact
details; and one of our own estimate reports uploaded as the document is flagged."""

from types import SimpleNamespace
from typing import Any

from app.llm.client import FakeClient
from app.services.documents.parsing import Page, ParsedDocument
from app.services.extraction.merge import about_tendering, merge_extractions
from app.services.extraction.tender import TenderExtraction, ai_read, verify_findings
from app.services.quick.config import quick_config
from app.services.quick.prefill import review_prefill

CFG = quick_config()

TERMS = (
    "The Purchaser shall be at liberty to recover such amount from the bills.\n"
    "The Bank guarantee shall remain valid for the balance amount.\n"
    "The decision of the arbitrator shall be final and binding on both parties.\n"
    "Payment shall be made online through the payment gateway of the bank of the Purchaser.\n"
    "Words importing persons shall include any company or association of individuals.\n"
)
DUTIES = (
    "Bidder shall provide hand-holding support to the team from the date of Go-Live.\n"
    "Bidder shall provide unlimited support as required as per the service window defined.\n"
    "The Bidder shall address all the errors and bugs in the functionality implemented.\n"
    "The Bidder shall provide role-based training to officials and keep the training records.\n"
)
SCOPE = "Patients can register using their name, mobile number, and email address."


Finding = dict[str, Any]


def _read(pages: list[str], features: list[Finding], others: list[Finding]) -> TenderExtraction:
    raw: Any = {
        "project_name": "Portal", "summary": "", "features": features, "other_features": others,
        "numbers": [], "unclear_points": [], "scope": [], "choices": [],
    }  # fmt: skip
    doc = ParsedDocument(
        kind="pdf", pages=[Page(i + 1, t) for i, t in enumerate(pages)], approximate_pages=False
    )
    client = FakeClient(lambda s, u: {"other_features": []} if "<already_found>" in u else raw)
    ex = verify_findings(CFG, doc, ai_read(client, CFG, doc).output, reader="ai", version="t")
    stored = SimpleNamespace(
        kind="rfp", filename="rfp.pdf", extraction={"reader": "ai"},
        page_texts=[{"page": i + 1, "text": t} for i, t in enumerate(pages)],
    )  # fmt: skip
    merged, _ = merge_extractions([(stored, ex)])  # type: ignore[list-item]
    return merged


def _ev(page: int, quote: str) -> list[dict[str, Any]]:
    return [{"page": page, "clause_ref": "", "quote": quote}]


def test_a_feature_found_only_in_the_contract_terms_is_offered_not_ticked() -> None:
    quote = "Payment shall be made online through the payment gateway"
    merged = _read([TERMS], [{"key": "payments", "evidence": _ev(1, quote)}], [])
    payments = next(f for f in merged.features if f.key == "payments")
    assert payments.outside_scope and not payments.suggested
    assert "payments" not in review_prefill(CFG, merged, "india").features


def test_a_page_of_the_vendors_duties_is_where_the_work_is_described() -> None:
    quote = "keep the training records"
    extra = {"name": "Training records", "description": "", "category": "module",
             "size": "S", "evidence": _ev(1, quote), "stories": [], "part_of": ""}  # fmt: skip
    merged = _read([DUTIES], [], [extra])
    assert [o.outside_scope for o in merged.other_features] == [False]
    assert [c.name for c in review_prefill(CFG, merged, "india").custom_features] == [
        "Training records"
    ]


def test_an_extra_found_only_in_the_terms_is_listed_but_not_priced() -> None:
    extra = {"name": "Bank guarantee tracker", "description": "", "category": "module",
             "size": "S", "evidence": _ev(1, "The Bank guarantee shall remain valid"),
             "stories": [], "part_of": ""}  # fmt: skip
    merged = _read([TERMS], [], [extra])
    assert [o.outside_scope for o in merged.other_features] == [True]
    assert review_prefill(CFG, merged, "india").custom_features == []


def test_registering_with_a_mobile_number_is_a_feature_not_contact_details() -> None:
    assert not about_tendering(SCOPE)
    assert about_tendering("Send it to helpdesk@example.com for activation.")
    assert about_tendering("Call the helpline at +91 11 2345 6789 for any query.")
    merged = _read([SCOPE], [{"key": "online_forms", "evidence": _ev(1, SCOPE)}], [])
    forms = next(f for f in merged.features if f.key == "online_forms")
    assert forms.suggested and not forms.outside_scope


def test_our_own_estimate_report_is_flagged() -> None:
    footer = (
        "Aakalan cost estimate — every figure is computed by a deterministic engine and "
        "traced to its source. Page 1"
    )
    assert _read(["Cost estimate: Clinic\n" + footer], [], []).own_report
    assert not _read([SCOPE], [], []).own_report

"""RailTel RFP checks (OPEN_QUESTIONS 219): the uptime is read from an SLA's penalty table in
code; an answer quoting only the tendering process (the portal's helpdesk for bidders, contact
details) is dropped, while a portal the software must connect to still counts; and a page of
contract terms lists nothing as "not priced yet"."""

from types import SimpleNamespace
from typing import Any

from app.llm.client import FakeClient
from app.services.documents.parsing import Page, ParsedDocument
from app.services.extraction.coverage import find_uncovered, terms_page
from app.services.extraction.merge import about_tendering, merge_extractions
from app.services.extraction.tender import TenderExtraction, ai_read, verify_findings
from app.services.extraction.uptime_terms import find_uptime
from app.services.quick.config import quick_config

CFG = quick_config()
assert CFG.uptime_terms is not None and CFG.coverage is not None
UPTIME = CFG.uptime_terms
COVERAGE = CFG.coverage

SLA_TABLE = (
    "4 O&M: All features and % Penalty to be deducted\n"
    "Availability of all functionalities to be Availability from Quarterly payment\n"
    "features and 100% available post <99.5% & >= 0.5%\n"
    "functionalities go-live 99%\n"
    "< 99% &>= 1%\n"
    "98%\n"
    "< 98% 2%\n"
)
HELPDESK = (
    "After completion of registration payment, you need to send your acknowledgement copy on "
    "our helpdesk e-mail address, ewizardhelpdesk@gmail.com for activation of your account."
)
PORTALS = (
    "Seamless integration with external and internal portals (e.g. MCA, e-tenders platform, CPPP,"
)


def _merged(text: str, choices: list[dict[str, Any]]) -> TenderExtraction:
    raw: Any = {
        "project_name": "Portal", "summary": "", "features": [], "other_features": [],
        "numbers": [], "unclear_points": [], "scope": [], "choices": choices,
    }  # fmt: skip
    doc = ParsedDocument(kind="pdf", pages=[Page(1, text)], approximate_pages=False)
    client = FakeClient(lambda s, u: {"other_features": []} if "<already_found>" in u else raw)
    ex = verify_findings(CFG, doc, ai_read(client, CFG, doc).output, reader="ai", version="t")
    stored = SimpleNamespace(
        kind="rfp", filename="rfp.pdf", page_texts=[{"page": 1, "text": text}],
        extraction={"reader": "ai"},
    )  # fmt: skip
    merged, _ = merge_extractions([(stored, ex)])  # type: ignore[list-item]
    return merged


def _choice(question: str, value: str, quote: str) -> dict[str, Any]:
    return {"question": question, "value": value,
            "evidence": [{"page": 1, "clause_ref": "", "quote": quote}]}  # fmt: skip


def test_the_first_penalty_threshold_is_the_uptime_asked_for() -> None:
    found = find_uptime(UPTIME, [(40, SLA_TABLE)])
    assert found is not None
    assert str(found.percent) == "99.5"
    assert found.evidence.page == 40
    assert "<99.5%" in found.evidence.quote


def test_a_stated_uptime_counts_and_penalty_shares_do_not() -> None:
    stated = find_uptime(UPTIME, [(1, "The portal shall have 99.9% uptime every month.")])
    assert stated is not None and str(stated.percent) == "99.9"
    assert (
        find_uptime(UPTIME, [(1, "Response time should achieve <5% of the 0.5% target.")]) is None
    )
    assert find_uptime(UPTIME, [(1, "Bids below 99.5% of the estimate are rejected.")]) is None


def test_the_sla_table_answers_the_downtime_question_over_the_reading() -> None:
    merged = _merged(
        SLA_TABLE, [_choice("availability", "high", "Availability of all functionalities")]
    )
    assert merged.choices["availability"].value == "normal"  # 99.5%, not 99.9%
    assert "<99.5%" in merged.choices["availability"].evidence[0].quote


def test_the_portals_helpdesk_for_bidders_is_not_a_helpdesk_to_provide() -> None:
    assert about_tendering(HELPDESK)
    assert not about_tendering(PORTALS)  # a portal the software connects to is real work
    merged = _merged(
        HELPDESK + "\n" + PORTALS,
        [_choice("helpdesk_scope", "yes", HELPDESK), _choice("integrations", "many", PORTALS)],
    )
    assert "helpdesk_scope" not in merged.choices
    assert merged.choices["integrations"].value == "many"


def test_a_page_of_contract_terms_lists_nothing() -> None:
    terms = (
        "The Purchaser shall be at liberty to recover such amount from the bills.\n"
        "The Bank guarantee shall remain valid for the balance amount.\n"
        "The decision of the arbitrator shall be final and binding on both parties.\n"
        "Words importing persons shall include any company or association of individuals.\n"
        "The contractor shall be solely responsible for any omission to notify a change.\n"
    )
    scope = (
        "4.3.1 The system shall let partners upload their credentials for the bank of records.\n"
        "The portal must send reminders before an empanelment expires.\n"
        "Users shall track their onboarding progress through the portal.\n"
        "The system shall generate a partnership confirmation letter.\n"
    )
    assert terms_page(COVERAGE, terms)
    assert not terms_page(COVERAGE, scope)
    nothing = _merged("Nothing here.", [])
    listed, _ = find_uncovered(COVERAGE, nothing, [("rfp.pdf", [(1, terms), (2, scope)])])
    assert {u.page for u in listed} == {2}

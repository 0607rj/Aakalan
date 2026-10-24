"""Support hours and dedicated support staff a document states, found in code (OPEN_QUESTIONS
157). The sentences are the RailTel e-Empanelment + Chatbot tender's (pages 12, 26 and 30)."""

from app.services.extraction.support_terms import find_support_hours, find_support_staff
from app.services.quick.config import SupportTerms, quick_config

PORTAL = (
    "Any queries relating to the process of online bid submission or queries relating to "
    "e-tender Portal in general may be directed to the 24x7 Helpdesk Support."
)
STAFF = (
    "A. Dedicated Personnel Allocation\nMinimum 2 offsite support resources assigned to RailTel "
    "during business hours for post-platform delivery and support for E-empanelment portal and "
    "chatbot platform."
)
ROUND_THE_CLOCK = (
    "D. Provide round-the-clock technical support and swift ticket resolution per SLAs."
)


def terms() -> SupportTerms:
    t = quick_config().support_terms
    assert t is not None
    return t


def pages(*texts: str) -> list[tuple[int, str]]:
    return list(enumerate(texts, start=1))


def test_round_the_clock_technical_support_is_on_call_and_the_conflict_is_kept() -> None:
    found = find_support_hours(terms(), pages(PORTAL, STAFF, ROUND_THE_CLOCK), "rfp.pdf")
    assert found is not None
    assert found.value == "on_call" and found.evidence.page == 3
    assert found.evidence.quote.startswith("Provide round-the-clock technical support")
    # "during business hours" on the staff sentence: a pre-bid query, not a silent choice
    assert found.conflict is not None and found.conflict.page == 2


def test_the_bidding_portals_own_helpdesk_does_not_count() -> None:
    assert find_support_hours(terms(), pages(PORTAL)) is None


def test_a_staffed_desk_round_the_clock_is_shifts() -> None:
    found = find_support_hours(terms(), pages("The bidder shall run a 24x7 helpdesk for users."))
    assert found is not None and found.value == "always" and found.conflict is None


def test_office_hours_and_a_fast_response() -> None:
    office = find_support_hours(terms(), pages("Support shall be given during office hours."))
    assert office is not None and office.value == "office"
    fast = "Severity 1 support tickets: response within 1 hour, resolution within 4 hours."
    found = find_support_hours(terms(), pages(fast))
    assert found is not None and found.value == "on_call"
    slow = "Support tickets: response within 8 hours."
    assert find_support_hours(terms(), pages(slow)) is None


def test_the_stated_support_staff() -> None:
    found = find_support_staff(terms(), pages(PORTAL, STAFF), "rfp.pdf")
    assert found is not None
    count, evidence = found
    assert count == 2 and evidence.page == 2


def test_onsite_staff_and_other_numbers_are_not_support_staff() -> None:
    onsite = "Two onsite support engineers shall be deployed at the client's office."
    assert find_support_staff(terms(), pages(onsite)) is None  # onsite_staff, read elsewhere
    hours = "Minimum 2 hours response time for support tickets assigned to the vendor."
    assert find_support_staff(terms(), pages(hours)) is None


def test_a_question_asking_which_hours_answers_nothing() -> None:
    # our own pre-bid query, e.g. in an exported report uploaded as the tender
    asked = "Kindly confirm whether support is required during office hours or round the clock."
    assert find_support_hours(terms(), pages(asked)) is None

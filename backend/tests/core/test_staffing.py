# Counts are Decimal; the tests compare them with plain numbers (equal at run time).
# mypy: disable-error-code="comparison-overlap"
"""Staff, support hours, helpdesk and chatbot level from the reading's staff lines
(services/extraction/staffing.py, OPEN_QUESTIONS 162).

The design cases (docs/answer-detection-design.md section 8) are updated to the user's rules of
2026-10-24 and use short quotes from the 8 tenders; the rule tests use short invented clauses.
Staff lines are what the reader finds (prompt v9); the code decides what is priced."""

from decimal import Decimal
from typing import Any

from app.models import Document
from app.services.extraction.merge import apply_code_checks
from app.services.extraction.staffing import apply_staffing, price_staff
from app.services.extraction.tender import (
    FoundChatbotSystems,
    FoundFeature,
    FoundStaffLine,
    FoundValue,
    PricedStaff,
    TenderExtraction,
    UnclearPoint,
    VerifiedEvidence,
)
from app.services.quick.config import QuickConfig, Staffing, quick_config

D = Decimal


def cfg() -> QuickConfig:
    return quick_config()


def rules() -> Staffing:
    r = cfg().staffing
    assert r is not None
    return r


def ev(quote: str, page: int = 1, document: str = "rfp.pdf") -> VerifiedEvidence:
    return VerifiedEvidence(page=page, clause_ref=f"Page {page}", quote=quote, document=document)


def line(role: str, count: float, quote: str, page: int = 1, **kw: Any) -> FoundStaffLine:
    return FoundStaffLine(role=role, count=D(str(count)), evidence=[ev(quote, page)], **kw)


def reading(
    lines: list[FoundStaffLine],
    *,
    choices: dict[str, str] | None = None,
    chatbot: bool = False,
    systems: str = "",
) -> TenderExtraction:
    c = cfg()
    found = {
        k: FoundValue(
            value=v, label=c.questions[k].option(v).label, evidence=[ev(f"{k} {v} stated")]
        )
        for k, v in (choices or {}).items()
    }
    features = (
        [FoundFeature(key="ai_chatbot", label="Chatbot", evidence=[ev("A chatbot for users.")])]
        if chatbot
        else []
    )
    return TenderExtraction(
        reader="ai",
        prompt_version="extract_tender_v9",
        project_name="Test",
        summary="",
        features=features,
        choices=found,
        numbers={},
        unclear_points=[],
        dropped_findings=0,
        staff_lines=lines,
        chatbot_buyer_systems=FoundChatbotSystems(systems=["core banking"], evidence=[ev(systems)])
        if systems
        else None,
    )


def docs(*texts: str) -> list[Document]:
    return [
        Document(
            filename="rfp.pdf",
            page_texts=[{"page": i, "text": t} for i, t in enumerate(texts, start=1)],
        )
    ]


def run(
    lines: list[FoundStaffLine], *texts: str, **kw: Any
) -> tuple[TenderExtraction, list[PricedStaff], list[UnclearPoint]]:
    """The code checks an upload gets: support terms on the page text, then the staff rules."""
    ex = reading(lines, **kw)
    apply_code_checks(ex, docs(*texts))
    return ex, ex.staffing or [], ex.unclear_points


def hours(ex: TenderExtraction) -> str | None:
    found = ex.choices.get("support_hours")
    return None if found is None else str(found.value)


def person_months(staff: list[PricedStaff], om_years: int = 5) -> Decimal:
    return sum((s.count * (s.months or 12 * om_years) for s in staff), D(0))


# --- rule tests: short invented clauses -----------------------------------------------------


def test_rule1_the_price_table_wins_over_the_terms() -> None:
    table = line(
        "support engineers",
        2,
        "Support engineers: 2 for 36 months.",
        9,
        in_price_table=True,
        location="vendor_site",
        months=36,
    )
    terms = line(
        "support engineers",
        4,
        "The vendor shall deploy four support engineers.",
        3,
        location="vendor_site",
        same_staff_as="support engineers",
    )
    staff, queries = price_staff(rules(), [table, terms])
    assert [(s.role, s.count, s.months) for s in staff] == [("support engineers", 2, 36)]
    assert len(queries) == 1 and queries[0].page == 3 and queries[0].answer == "support_staff"
    assert "price schedule" in queries[0].prebid_query and "page 9" in queries[0].prebid_query


def test_rule1_the_same_staff_stated_alike_raise_no_query() -> None:
    table = line(
        "developers",
        2,
        "Two developers at the client office.",
        9,
        in_price_table=True,
        location="client_site",
    )
    terms = line(
        "developers",
        2,
        "Two developers shall sit at the client office.",
        3,
        location="client_site",
        same_staff_as="developers",
    )
    staff, queries = price_staff(rules(), [table, terms])
    assert len(staff) == 1 and not queries


def test_rule2_round_the_clock_without_shifts_is_on_call() -> None:
    ex, _, _ = run([], "The portal uptime shall be 99.5% on a 24x7 basis.")
    assert hours(ex) == "on_call"
    ex, _, _ = run(
        [], "Support shall be given 24x7 by the vendor.", choices={"support_hours": "always"}
    )
    assert hours(ex) == "on_call"


def test_rule3_a_committed_round_the_clock_team_per_shift_is_seats() -> None:
    """Invented committed table: 1 L1 per shift, 24x7, a firm number."""
    l1 = line(
        "L1 engineers",
        1,
        "L1 engineers per shift on a 24x7 basis: 1.",
        5,
        count_basis="per_shift",
        round_the_clock=True,
        in_price_table=True,
        location="client_site",
    )
    ex, staff, queries = run([l1], "Helpdesk staffed in three shifts.")
    assert [(s.count, s.seats, s.call_off) for s in staff] == [(1, True, False)]
    assert hours(ex) == "always" and not [q for q in queries if q.answer == "support_hours"]


def test_rule3_call_off_staff_are_priced_as_written_and_on_call() -> None:
    """Invented call-off table: the buyer may ask for any number, 24x7, per shift."""
    team = line(
        "L1, L2 and L3 resources",
        3,
        "The buyer at its discretion may ask any number of resources on 24x7 basis.",
        8,
        count_basis="per_shift",
        round_the_clock=True,
        buyer_sets_headcount=True,
        in_price_table=True,
        location="client_site",
    )
    ex, staff, queries = run([team])
    assert [(s.kind, s.count, s.seats, s.call_off) for s in staff] == [("onsite", 3, False, True)]
    assert hours(ex) == "on_call"
    answers = sorted(q.answer for q in queries)
    assert answers == ["onsite_staff", "support_hours"]


def test_rule4_place_not_stated_is_offsite_with_a_query() -> None:
    staff, queries = price_staff(
        rules(), [line("support staff", 2, "Two support staff for the AMC.")]
    )
    assert staff[0].kind == "support" and len(queries) == 1
    assert "priced them offsite" in queries[0].prebid_query


def test_rule4_a_table_row_takes_the_place_its_terms_state() -> None:
    table = line(
        "developers", 2, "Technical support centre with 2 developers.", 9, in_price_table=True
    )
    terms = line(
        "developers",
        2,
        "Two developers working remotely.",
        3,
        location="vendor_site",
        same_staff_as="developers",
    )
    staff, queries = price_staff(rules(), [table, terms])
    assert staff[0].kind == "support" and not queries


def test_rule5_duration_comes_from_the_staff_line_and_build_staff_are_not_priced() -> None:
    desk = line(
        "helpdesk professionals",
        2,
        "Helpdesk of 2 professionals for 2 years.",
        months=24,
        location="vendor_site",
    )
    builder = line("architect", 1, "An architect during development.", phase="build")
    months = line(
        "resource-months",
        60,
        "Offsite support: 60 resource-months.",
        count_basis="resource_months",
        location="vendor_site",
    )
    staff, _ = price_staff(rules(), [desk, builder, months])
    assert [(s.role, s.count, s.months) for s in staff] == [
        ("helpdesk professionals", 2, 24),
        ("resource-months", 1, 60),
    ]


def test_rule6_an_unclear_quantity_is_priced_as_read_with_a_query() -> None:
    unclear = line(
        "developers",
        2,
        "Support centre with 2 nos of developers 02.",
        quantity_unclear=True,
        note="02: years or developers",
        location="vendor_site",
    )
    staff, queries = price_staff(rules(), [unclear])
    assert staff[0].count == 2 and len(queries) == 1
    assert "02: years or developers" in queries[0].prebid_query


def test_rule7_chatbot_complex_only_with_the_buyers_systems() -> None:
    ex, _, _ = run([], chatbot=True, choices={"chatbot_task": "advanced"})
    assert "chatbot_task" not in ex.choices  # no buyer's systems: the usual answer
    ex, _, _ = run([], chatbot=True, systems="Integrate with the Bank's core banking system.")
    assert ex.choices["chatbot_task"].value == "advanced"


def test_helpdesk_only_when_asked_for() -> None:
    ex, _, _ = run([], "Provide a service desk for users.")
    assert ex.choices["helpdesk_scope"].value == "yes"
    ex, _, _ = run([], "The vendor fixes bugs.", choices={"helpdesk_scope": "yes"})
    assert "helpdesk_scope" not in ex.choices
    portal = "Queries on bid submission may be sent to the GeM helpdesk."
    ex, _, _ = run([], portal)
    assert "helpdesk_scope" not in ex.choices


def test_numbers_are_replaced_by_the_staff_lines() -> None:
    ex = reading([line("developer", 1, "One developer onsite.", location="client_site")])
    ex.numbers["onsite_staff"] = FoundValue(value=4, label="4", evidence=[ev("Four people.")])
    apply_staffing(cfg(), ex, docs())
    assert "onsite_staff" not in ex.numbers and ex.staffing and ex.staffing[0].count == 1


# --- the design cases, updated to the rules (short quotes from the 8 tenders) ---------------

TRADE_NOTE = (
    "the quantity mentioned is indicative in nature and does not construe a firm commitment"
)


def test_o1_h4_iob_trade_cost_tables_win_and_are_call_off() -> None:
    def row(role: str, rtc: bool = True) -> FoundStaffLine:
        return line(
            role,
            1,
            TRADE_NOTE,
            118,
            count_basis="per_shift",
            location="client_site",
            months=60,
            round_the_clock=rtc,
            buyer_sets_headcount=True,
            in_price_table=True,
        )

    l1_terms = line(
        "L1 onsite",
        4,
        "minimum 4 persons in all on a 2-shift basis (8am to 8pm)",
        87,
        location="client_site",
        round_the_clock=True,
        same_staff_as="onsite L1 support",
    )
    ex, staff, queries = run(
        [
            row("onsite L1 support"),
            row("onsite L2 support"),
            row("onsite developer", False),
            l1_terms,
        ],
        "Help desk on 24 X 7 X 365 basis.",
    )
    assert [(s.count, s.months, s.call_off, s.seats) for s in staff] == [(1, 60, True, False)] * 3
    assert hours(ex) == "on_call"  # call-off staff "on 24x7" are on call (H4)
    assert any(q.page == 87 and "page 118" in q.prebid_query for q in queries)


def test_o2_ewaste_developers_at_head_office() -> None:
    staff, _ = price_staff(
        rules(),
        [
            line(
                "developer at HO",
                1,
                "along with 1 developer at CPCB head office",
                55,
                location="client_site",
                months=60,
                in_price_table=True,
            ),
            line(
                "second developer at HO",
                1,
                "along with 2 developers at CPCB Head Office",
                55,
                location="client_site",
                months=12,
                in_price_table=True,
            ),
        ],
    )
    assert person_months(staff) == 72 and {s.kind for s in staff} == {"onsite"}


def test_o3_h6_iob_chatbot() -> None:
    dev = line(
        "onsite developer",
        1,
        "costing for one onsite developer",
        57,
        location="client_site",
        phase="whole_contract",
    )
    l2 = line(
        "onsite L2",
        1,
        "Onsite support engineer (L2 level) for initial 1 year",
        103,
        location="client_site",
        months=12,
    )
    team = line(
        "L1, L2 and L3",
        3,
        "resources shall be required to work on 24*7 basis",
        115,
        count_basis="per_shift",
        round_the_clock=True,
        buyer_sets_headcount=True,
        in_price_table=True,
    )
    ex, staff, queries = run([dev, l2, team])
    assert [(s.kind, s.count, s.months, s.call_off) for s in staff] == [
        ("onsite", 1, None, False),
        ("onsite", 1, 12, False),
        ("support", 3, None, True),
    ]
    assert hours(ex) == "on_call"
    assert sorted(q.answer for q in queries) == ["support_hours", "support_staff", "support_staff"]


def test_o4_h1_canara_table_d_and_onsite_24x7() -> None:
    table = line(
        "offsite support",
        1,
        "Dedicated Offsite Support charges",
        58,
        location="vendor_site",
        months=60,
        in_price_table=True,
        buyer_sets_headcount=True,
    )
    terms = line(
        "onsite resources",
        0,
        "provide onsite resources on 365x24x7",
        4,
        location="client_site",
        round_the_clock=True,
        same_staff_as="offsite support",
    )
    ex, staff, queries = run(
        [table, terms],
        "The bidder shall provide centralized complaint booking/lodging facility to the bank.",
    )
    assert [(s.kind, s.count, s.months) for s in staff] == [("support", 1, 60)]
    assert hours(ex) == "on_call" and ex.choices["helpdesk_scope"].value == "yes"
    conflict = next(q for q in queries if "price schedule" in q.prebid_query)
    assert "an unstated number of onsite resources" in conflict.prebid_query


def test_o5_meghalaya_onsite_team() -> None:
    lines = [
        line("Project Manager", 1, "Project Manager 1 deployed onsite", location="client_site"),
        line("System Analyst", 2, "System Analyst 2 deployed onsite", location="client_site"),
        line(
            "Database Administrator", 1, "Database Administrator 1 onsite", location="client_site"
        ),
        line(
            "UI/UX Designer",
            1,
            "UI/UX Designer 1 deployed onsite",
            location="client_site",
            quantity_unclear=True,
            note="no deployment period stated",
        ),
    ]
    staff, queries = price_staff(rules(), lines)
    assert sum(s.count for s in staff) == 5 and len(queries) == 1


def test_o6_s3_h2_tyre_support_centre_not_counted_twice() -> None:
    table = line(
        "support centre developers",
        3,
        "technical support center with 3 nos of developers",
        37,
        months=60,
        in_price_table=True,
    )
    programmers = line(
        "programmer cum coordinator",
        3,
        "Three persons (programmer cum coordinator)",
        17,
        location="client_site",
        same_staff_as="support centre developers",
    )
    desk = line(
        "service desk developers",
        2,
        "Service desk operation for six years",
        35,
        same_staff_as="support centre developers",
    )
    ex, staff, queries = run(
        [table, programmers, desk], "The organization shall ensure 24 x 7 operations."
    )
    assert [(s.kind, s.count, s.months) for s in staff] == [("onsite", 3, 60)]
    assert len(queries) == 1 and queries[0].page == 35  # the service desk's 2 developers
    assert hours(ex) == "on_call"


def test_o7_s2_h3_iob_website() -> None:
    onsite = line(
        "onsite resource",
        1,
        "1 resource must be available at the Bank premises",
        71,
        location="client_site",
    )
    offsite = line("off-site team", 5, "Team of not less than 5 people", 71, location="vendor_site")
    ex, staff, _ = run([onsite, offsite], "24*7 support for website related malfunctions.")
    assert [(s.kind, s.count, s.months) for s in staff] == [
        ("onsite", 1, None),
        ("support", 5, None),
    ]
    assert hours(ex) == "on_call"


def test_s1_h5_ewaste_two_support_lines_and_helpdesk() -> None:
    desk = line(
        "helpdesk professionals",
        2,
        "Helpdesk support comprising of 2",
        55,
        months=24,
        in_price_table=True,
    )
    centre = line(
        "support centre developers",
        2,
        "with 2 nos of developers till atleast 2",
        55,
        months=24,
        in_price_table=True,
        quantity_unclear=True,
        note="02: years or developers",
    )
    ex, staff, queries = run(
        [desk, centre], "Provide 24x7 support through a helpdesk to stakeholders."
    )
    assert person_months(staff) == 96
    assert hours(ex) == "on_call" and ex.choices["helpdesk_scope"].value == "yes"
    assert len(queries) == 3  # place of each line, and the unclear "02"


def test_s4_s5_battery_support_centre_and_full_stack_developer() -> None:
    centre = line(
        "support centre developers",
        2,
        "with 2 nos of developers till at least 2",
        3,
        months=24,
        in_price_table=True,
    )
    remote = line(
        "remote IT staff",
        3,
        "a senior IT Expert and two IT Developers working remotely",
        14,
        location="vendor_site",
        same_staff_as="support centre developers",
    )
    full_stack = line(
        "full stack developer",
        1,
        "The full stack developer placed in the CPCB HO",
        15,
        location="client_site",
        quantity_unclear=True,
        note="may be one of the 2",
    )
    staff, queries = price_staff(rules(), [centre, remote, full_stack])
    assert [(s.kind, s.count, s.months) for s in staff] == [("support", 2, 24), ("onsite", 1, None)]
    assert len(queries) == 2


def test_h7_no_hours_stated_leaves_the_usual_answer() -> None:
    ex, _, _ = run(
        [line("Project Manager", 1, "Project Manager deployed onsite", location="client_site")]
    )
    assert hours(ex) is None


def test_c1_c2_c3_c4_chatbot_level() -> None:
    bank = "System should provide support for integration of Bank's Systems"
    ex, _, _ = run([], chatbot=True, systems=bank)  # canara, iob-chatbot
    assert ex.choices["chatbot_task"].value == "advanced"
    ex, _, _ = run([], chatbot=True, choices={"chatbot_task": "simple"})  # ewaste FAQs
    assert ex.choices["chatbot_task"].value == "simple"
    ex, _, _ = run([], chatbot=True, choices={"chatbot_task": "advanced"})  # iob-trade
    assert "chatbot_task" not in ex.choices


def test_p1_both_readings_are_not_priced() -> None:
    """Pricing both readings (a wider range) stays switched off: one staff list, no options."""
    staff, _ = price_staff(
        rules(), [line("developers", 2, "Two developers for support.", quantity_unclear=True)]
    )
    assert len(staff) == 1


def test_staff_names_that_do_the_engines_own_work() -> None:
    """Onsite PMs are the O&M project manager, onsite developers / L2-L3 do the upkeep; other
    staff and offsite support staff do other work (OPEN_QUESTIONS 166)."""
    from app.services.quick.service import StaffItem, _staff_covers

    def covers(role: str) -> str:
        return _staff_covers(cfg(), StaffItem(kind="onsite", role=role, count=Decimal(1)))

    assert covers("Project Manager") == "management"
    assert covers("Team Leader cum Developer") == "management"
    assert covers("Software Developers") == "upkeep"
    assert covers("L2 support engineer") == "upkeep"
    assert covers("Helpdesk operator (L1)") == ""
    assert covers("Database Administrator") == ""

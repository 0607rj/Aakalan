"""Handover at the end of the contract on small projects (parameter sets v27+, OPEN_QUESTIONS
179): on lean delivery it is the smaller of the size band's days and a share of the build, and
a deadline too short to build in reports the fastest one that still gets a price."""

from collections.abc import Callable
from decimal import Decimal

from app.services.engine.core import calculate, schedule
from app.services.engine.inputs import EstimateInput
from app.services.seeding.reference import ReferenceData
from tests.engine.conftest import answer, tweak


def small(
    golden: Callable[[str], EstimateInput], reference: ReferenceData, params: str
) -> EstimateInput:
    """The small golden project, sized small (lean delivery), with formal reports and meetings
    (so a handover is priced)."""
    inp = tweak(
        golden("small"),
        taxonomy=reference.taxonomy,
        catalog=reference.catalog_version("v5"),
        rate_card=reference.rate_card("v11"),
        parameters=reference.parameter_set(params),
    )
    return answer(answer(inp, "governance_overheads", True), "project_size", "small")


def exit_line(inp: EstimateInput) -> tuple[str, int]:
    result = calculate(inp)
    line = next(ln for ln in result.lines if ln.bucket == "commercial.exit_management")
    return line.formula_id, line.likely_paise


def test_handover_follows_the_work_on_lean_delivery(
    golden: Callable[[str], EstimateInput], reference: ReferenceData
) -> None:
    before_formula, before = exit_line(small(golden, reference, "v26"))
    after_formula, after = exit_line(small(golden, reference, "v27"))
    assert (before_formula, after_formula) == ("commercial.exit.v1", "commercial.exit.v2")
    build_pd = calculate(small(golden, reference, "v27")).timeline.build_effort_pd
    share = Decimal("0.02")
    assert share * build_pd < 10  # the band's 10 days are more than the share of this build
    # same handover role and rate: the price falls with the days
    assert abs(Decimal(after) / before - share * build_pd / 10) < Decimal("0.001")


def test_fastest_deadline_is_the_shortest_that_gets_a_price(
    golden: Callable[[str], EstimateInput], reference: ReferenceData
) -> None:
    inp = small(golden, reference, "v27")
    plan = schedule(inp)
    natural = plan.timeline.natural_duration_months
    assert plan.timeline.status == "natural"
    assert plan.fastest_months == (natural * Decimal("0.5")).quantize(Decimal("0.1"))

    too_short = answer(inp, "deadline_months", plan.fastest_months / 2)
    result = calculate(too_short)
    assert not result.feasible and result.infeasibility is not None
    assert result.infeasibility.minimum_feasible_months == plan.fastest_months
    assert schedule(too_short).timeline.status == "not_feasible"
    assert calculate(answer(inp, "deadline_months", plan.fastest_months)).feasible

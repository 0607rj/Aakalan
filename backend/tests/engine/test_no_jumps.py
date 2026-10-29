"""Prices that grow smoothly (parameter sets v29+, OPEN_QUESTIONS 182): a deadline longer than
the natural build time is built in the natural time, and helpdesk seats follow the registered
users on a straight line instead of stepping at 10,000 / 1 lakh / 10 lakh."""

from collections.abc import Callable
from decimal import Decimal

from app.services.engine.core import calculate
from app.services.engine.inputs import EstimateInput
from app.services.seeding.reference import ReferenceData
from tests.engine.conftest import answer, tweak


def medium(
    golden: Callable[[str], EstimateInput], reference: ReferenceData, params: str
) -> EstimateInput:
    return tweak(
        golden("medium"),
        taxonomy=reference.taxonomy,
        catalog=reference.catalog_version("v5"),
        rate_card=reference.rate_card("v11"),
        parameters=reference.parameter_set(params),
    )


def test_a_longer_deadline_is_built_in_the_natural_time(
    golden: Callable[[str], EstimateInput], reference: ReferenceData
) -> None:
    for params in ("v28", "v29"):
        inp = answer(medium(golden, reference, params), "deadline_months", None)
        natural = calculate(inp)
        months = natural.timeline.natural_duration_months
        longer = calculate(answer(inp, "deadline_months", (months * 3).quantize(Decimal(1))))
        if params == "v28":  # the management, travel and test servers ran over the deadline
            assert longer.timeline.status == "extended"
            assert longer.timeline.programme_duration_months > months
            assert longer.totals and natural.totals
            assert longer.totals.p50_paise > natural.totals.p50_paise
        else:  # the team builds in its natural time: a longer deadline never costs more
            assert longer.timeline.status == "natural"
            assert longer.timeline.delivery_duration_months == months
            assert longer.timeline.programme_duration_months == months
            assert longer.totals == natural.totals


def seats(inp: EstimateInput, users: int) -> Decimal:
    """Helpdesk person-days of year 1 per coverage FTE and working year: the seats priced."""
    inp = answer(answer(inp, "helpdesk_in_scope", True), "users_total", users)
    line = next(ln for ln in calculate(inp).lines if ln.line_key == "run.helpdesk/helpdesk/y1")
    step = next(s for s in line.trace.steps if s.label == "helpdesk person-days")
    seats, coverage, year = (Decimal(x) for x in step.expression.split(" × "))
    assert step.value == seats * coverage * year
    return seats


def test_helpdesk_seats_grow_with_the_users(
    golden: Callable[[str], EstimateInput], reference: ReferenceData
) -> None:
    old, new = medium(golden, reference, "v28"), medium(golden, reference, "v29")
    assert [seats(old, n) for n in (10_000, 10_001, 100_000)] == [1, 2, 2]
    smooth = [seats(new, n) for n in (5_000, 10_000, 10_001, 55_000, 100_000, 20_000_000)]
    assert smooth[0] == smooth[1] == 1  # flat below the first point
    assert 1 < smooth[2] < Decimal("1.0001")  # one user more, no step
    assert smooth[3] == Decimal("1.5")
    assert smooth[4] == 2
    assert smooth[5] == 8  # flat above the last point

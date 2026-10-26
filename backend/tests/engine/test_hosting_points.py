"""Hosting by the actual number online (parameter sets v26+ with rate card v11+, OPEN_QUESTIONS
171): a straight line between the nearest price points instead of the middle of the load band,
so there is no jump at a band edge and 500 online costs less than 1,000."""

from collections.abc import Callable
from decimal import Decimal

from app.services.engine.core import calculate
from app.services.engine.formulas import FORMULAS
from app.services.engine.inputs import EstimateInput
from app.services.engine.outputs import CostLineOut
from app.services.seeding.reference import ReferenceData
from tests.engine.conftest import answer
from tests.engine.test_one_line import project


def year_one(inp: EstimateInput) -> CostLineOut:
    return next(ln for ln in calculate(inp).lines if ln.bucket == "run.hosting" and ln.year == 1)


def at(
    golden: Callable[[str], EstimateInput],
    reference: ReferenceData,
    peak: int,
    sla: str = "99.5",
    rates: str = "v11",
) -> CostLineOut:
    inp = answer(project(golden, reference, "v26", rates), "uptime_sla", sla)
    return year_one(answer(inp, "peak_concurrent_users", peak))


def test_the_formula_is_registered() -> None:
    assert "hosting.bundle.v2" in FORMULAS


def test_hosting_follows_the_number_online(
    golden: Callable[[str], EstimateInput], reference: ReferenceData
) -> None:
    prices = [at(golden, reference, n).likely_paise for n in (100, 200, 300, 400, 500, 1000)]
    assert prices == sorted(prices) and len(set(prices)) == len(prices)


def test_no_jump_at_a_band_edge(
    golden: Callable[[str], EstimateInput], reference: ReferenceData
) -> None:
    """200 -> 201 online was one small server -> two servers, databases and a load balancer."""
    before = at(golden, reference, 200).likely_paise
    after = at(golden, reference, 201).likely_paise
    assert after < before * Decimal("1.05")


def test_between_two_points_is_a_straight_line(
    golden: Callable[[str], EstimateInput], reference: ReferenceData
) -> None:
    """500 online: one sixth of the way from one server at 400 to two at 1,000."""
    line = at(golden, reference, 500)
    assert line.formula_id == "hosting.bundle.v2"
    one = at(golden, reference, 400).likely_paise
    two = at(golden, reference, 1000).likely_paise
    assert abs(line.likely_paise - (one + (two - one) / 6)) <= 2  # paise rounding


def test_99_9_stays_on_two_servers_at_every_point(
    golden: Callable[[str], EstimateInput], reference: ReferenceData
) -> None:
    assert at(golden, reference, 300, "99.9").likely_paise > at(golden, reference, 300).likely_paise


def test_beyond_the_last_point_the_line_carries_on(
    golden: Callable[[str], EstimateInput], reference: ReferenceData
) -> None:
    assert at(golden, reference, 40000).likely_paise > at(golden, reference, 20000).likely_paise


def test_without_the_points_hosting_keeps_the_band_price(
    golden: Callable[[str], EstimateInput], reference: ReferenceData
) -> None:
    line = at(golden, reference, 500, rates="v10")
    assert line.formula_id == "hosting.bundle.v1"

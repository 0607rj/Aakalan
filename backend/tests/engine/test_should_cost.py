"""Parameter sets v13-v15: smooth size factor by feature points, lean management without
formal reporting, should-cost with a market check."""

from collections.abc import Callable
from decimal import Decimal

import pytest

from app.services.engine.core import calculate
from app.services.engine.inputs import EstimateInput
from app.services.engine.money import ONE, quantize
from app.services.seeding.reference import ReferenceData
from tests.engine.conftest import answer, tweak

D = Decimal


@pytest.fixture
def priced(
    golden: Callable[[str], EstimateInput], reference: ReferenceData
) -> Callable[..., EstimateInput]:
    """The small golden project on current India reference data, with the given answers."""

    def make(version: str, catalog: str = "v5", **answers: object) -> EstimateInput:
        inp = tweak(
            golden("small"),
            taxonomy=reference.taxonomy,
            catalog=reference.catalog_version(catalog),
            rate_card=reference.rate_card("v5"),
            parameters=reference.parameter_set(version),
        )
        for key, value in answers.items():
            inp = answer(inp, key, value)
        return inp

    return make


def test_size_factor_follows_feature_points_smoothly(priced: Callable[..., EstimateInput]) -> None:
    """v13: one more feature point moves the build effort a little, never in a jump."""
    efforts = [
        calculate(
            priced("v13", "v4", project_size="medium", size_points=p)
        ).timeline.build_effort_pd
        for p in (10, 11, 12)
    ]
    assert efforts[0] < efforts[1] < efforts[2]
    assert efforts[1] / efforts[0] < D("1.1")  # no 70% jump at a size boundary
    without = calculate(priced("v13", "v4", project_size="medium"))  # no points: size factor
    assert without.timeline.build_effort_pd != efforts[0]


def test_lean_management_without_formal_reporting(priced: Callable[..., EstimateInput]) -> None:
    """v13+: a medium project without reports and meetings prices management with the work."""
    lean = calculate(priced("v13", "v4", project_size="medium", governance_overheads=False))
    full = calculate(priced("v13", "v4", project_size="medium", governance_overheads=True))
    pm = {r.line_key: r for r in lean.lines if r.line_key == "programme.project_management/pm"}[
        "programme.project_management/pm"
    ]
    assert pm.formula_id == "programme.pm.v2"
    full_pm = next(r for r in full.lines if r.line_key == "programme.project_management/pm")
    assert full_pm.formula_id == "programme.pm.v1"


def test_market_check_is_p50_times_the_band(priced: Callable[..., EstimateInput]) -> None:
    """v14+: real contracts of this size against this estimate, computed by the engine."""
    inp = priced("v15", project_size="small")
    result = calculate(inp)
    assert result.market is not None and result.totals is not None
    band = inp.parameters.calibration.market_by_size["small"]  # type: ignore[union-attr]
    p50 = D(result.totals.p50_paise)
    assert result.market.low_paise == int(quantize(p50 * band.low, ONE))
    assert result.market.high_paise == int(quantize(p50 * band.high, ONE))
    assert result.market.projects == band.projects
    assert calculate(priced("v13", "v4", project_size="small")).market is None  # not should-cost


def test_should_cost_has_no_size_factor(priced: Callable[..., EstimateInput]) -> None:
    """v15: the same work costs the same effort whatever the size class; only the effort level
    (checked against real effort) applies."""
    small = calculate(priced("v15", project_size="small")).timeline.build_effort_pd
    large = calculate(priced("v15", project_size="large")).timeline.build_effort_pd
    assert small == large
    v14 = calculate(priced("v14", project_size="small")).timeline.build_effort_pd
    assert abs(small / v14 - D("1.4")) < D("0.01")  # v15's effort multiplier

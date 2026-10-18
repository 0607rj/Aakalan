"""Private and small-business calibration (parameter sets v6 / us-v5): lean delivery caps,
segment effort factor and the shared back-tested model error."""

from collections.abc import Callable
from decimal import Decimal

import pytest

from app.services.calibration.backtest import band_ratio, today_value, with_dials
from app.services.engine.core import calculate
from app.services.engine.inputs import EstimateInput
from app.services.engine.outputs import CostLineOut, EstimateResult
from app.services.seeding.reference import ReferenceData
from tests.engine.conftest import answer, tweak

D = Decimal


@pytest.fixture
def priced(
    golden: Callable[[str], EstimateInput], reference: ReferenceData
) -> Callable[..., EstimateInput]:
    """The small golden project on the current India reference data, for a buyer segment."""

    def make(segment: str, version: str = "v6", **answers: object) -> EstimateInput:
        inp = tweak(
            golden("small"),
            taxonomy=reference.taxonomy,
            catalog=reference.catalog,
            rate_card=reference.rate_card("v3"),
            parameters=reference.parameter_set(version),
        )
        for key, value in {"buyer_segment": segment, **answers}.items():
            inp = answer(inp, key, value)
        return inp

    return make


def line(result: EstimateResult, key: str) -> CostLineOut:
    return next(ln for ln in result.lines if ln.line_key == key)


def test_lean_caps_management_for_small_business_only(priced: Callable[..., EstimateInput]) -> None:
    small = calculate(priced("small_business"))
    gov = calculate(priced("government"))
    pm_small = line(small, "programme.project_management/pm")
    pm_gov = line(gov, "programme.project_management/pm")
    assert pm_small.formula_id == "programme.pm.v2" and pm_gov.formula_id == "programme.pm.v1"
    share = priced("small_business").parameters.lean.pm_share_of_build_pd  # type: ignore[union-attr]
    pm_pd = sum(pm_small.role_pd.values(), D(0))
    assert pm_pd <= share * small.timeline.build_effort_pd + D("0.000001")
    hyper = line(small, "go_live.hypercare/team")
    assert hyper.formula_id == "golive.hypercare.v2"


def test_segment_factor_cuts_build_effort(priced: Callable[..., EstimateInput]) -> None:
    gov = calculate(priced("government"))
    small = calculate(priced("small_business"))
    factor = priced("small_business").parameters.calibration.segment_effort_multiplier[  # type: ignore[union-attr]
        "small_business"
    ]
    ratio = small.timeline.build_effort_pd / gov.timeline.build_effort_pd
    assert ratio == factor
    assert small.totals and gov.totals and small.totals.likely_paise < gov.totals.likely_paise


def test_model_error_widens_range_for_commercial_segments(
    priced: Callable[..., EstimateInput],
) -> None:
    with_error = calculate(priced("small_business"))
    without = calculate(priced("small_business", version="v5"))  # no model spread in v5
    assert with_error.calibration.model_spread is not None
    assert without.calibration.model_spread is None
    assert with_error.totals and without.totals

    def width(r: EstimateResult) -> float:
        assert r.totals
        return (r.totals.p90_paise - r.totals.p10_paise) / r.totals.p50_paise

    assert width(with_error) > 2 * width(without)
    gov = calculate(priced("government"))
    assert gov.calibration.model_spread is None  # government ranges unchanged


def test_today_value_and_bands() -> None:
    assert today_value(10_000, 2024, 2026, D("0.08")) == 11_664
    assert today_value(10_000, 2027, 2026, D("0.08")) == 10_000  # never deflated
    assert band_ratio(150, 100, 200) == 1.0
    assert band_ratio(50, 100, 200) == 0.5
    assert band_ratio(400, 100, 200) == 2.0
    assert band_ratio(300, 100, None) == 3.0


def test_commercial_factor_touches_build_effort_only(reference: ReferenceData) -> None:
    params = with_dials(reference.parameter_set("v6"), D(1), D(1), {"private": D("0.5")})
    assert params.calibration is not None
    assert params.calibration.segment_effort_multiplier == {
        "private": D("0.5"),
        "small_business": D("0.19"),
    }
    assert params.calibration.segment_run_multiplier == {}

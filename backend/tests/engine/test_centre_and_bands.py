"""Parameter set v23 (OPEN_QUESTIONS 160): the shared model factor centred on its median (it
widens the range without lifting P50), named as a range driver, and size-band values blended
across the band edges (one person-day more never steps the price)."""

from collections.abc import Callable
from decimal import Decimal

import numpy as np
import pydantic
import pytest

from app.models import Estimate
from app.services.engine.commercial import Factors
from app.services.engine.context import PricingContext
from app.services.engine.core import calculate
from app.services.engine.inputs import EstimateInput
from app.services.engine.reference import Timeline
from app.services.engine.simulation import (
    MODEL_DRIVER,
    simulate,
    triangular_inverse,
)
from app.services.engine.timeline import band_value
from app.services.quick.service import _beyond_range
from app.services.seeding.reference import ReferenceData
from tests.engine.conftest import tweak

D = Decimal
SPREAD = (D("0.7"), D("1.35"))  # v21-v23 medium_large


@pytest.fixture
def v23(golden: Callable[[str], EstimateInput], reference: ReferenceData) -> EstimateInput:
    return tweak(
        golden("small"),
        taxonomy=reference.taxonomy,
        catalog=reference.catalog_version("v5"),
        rate_card=reference.rate_card("v9"),
        parameters=reference.parameter_set("v23"),
    )


def pm_fte(inp: EstimateInput, build_pd: str) -> Decimal:
    ctx = PricingContext(inp)
    t = ctx.builder(
        line_key="programme.project_management/test",
        stage="programme",
        bucket="programme.project_management",
        year=0,
        label="test",
        formula_id="programme.pm.v1",
    )
    return band_value(t, D(build_pd), "pm_fte")


def test_band_values_blend_across_the_edge(v23: EstimateInput, reference: ReferenceData) -> None:
    bands = v23.parameters.timeline.size_bands
    small, medium = bands[0].pm_fte, bands[1].pm_fte
    assert pm_fte(v23, "700") == small and pm_fte(v23, "1300") == medium
    assert pm_fte(v23, "1000") == (small + medium) / 2
    assert abs(pm_fte(v23, "1001") - pm_fte(v23, "999")) < D("0.01")
    # before v23 the value steps at the edge
    v22 = tweak(v23, parameters=reference.parameter_set("v22"))
    assert pm_fte(v22, "1000") == small and pm_fte(v22, "1001") == medium


def test_overlapping_blends_are_rejected(v23: EstimateInput) -> None:
    timeline = v23.parameters.timeline.model_dump()
    with pytest.raises(pydantic.ValidationError, match="overlap"):
        Timeline.model_validate({**timeline, "size_band_blend_share": "0.7"})


def constant_simulation(inp: EstimateInput, centre: str | None) -> int:
    """P50 of the estimate's base lines held at their likely values, with the shared factor
    (centred on its mode or median) or without it (None)."""
    result = calculate(inp)
    lines = [
        ln.model_copy(update={"low_paise": ln.likely_paise, "high_paise": ln.likely_paise})
        for ln in result.lines
        if not ln.derived
    ]
    zero = Factors(*[D(0)] * 11)
    spread = SPREAD if centre else None
    sim = simulate(lines, zero, inp.seed, 4000, inp.taxonomy, spread, centre or "mode")
    return sim.p50_paise


def test_the_shared_factor_centred_on_its_median_does_not_lift_p50(v23: EstimateInput) -> None:
    plain = constant_simulation(v23, None)
    median = float(triangular_inverse(np.array([0.5]), 0.3, 1.0, 2.35)[0])
    assert median > 1.15  # the lopsided triangle's median, the lift v21-v22 carried
    assert abs(constant_simulation(v23, "mode") / plain - median) < 0.02
    assert abs(constant_simulation(v23, "median") / plain - 1) < 0.02


def test_the_shared_factor_is_a_range_driver(v23: EstimateInput) -> None:
    drivers = calculate(v23).top_drivers
    assert drivers and drivers[0].bucket == MODEL_DRIVER
    assert drivers[0].name.startswith("Shared: model error")
    assert sum(d.variance_share for d in drivers) <= D("1.001")


def test_an_open_answer_beyond_the_range() -> None:
    est = Estimate(p10_paise=80, p50_paise=100, p90_paise=150)
    assert not _beyond_range(est, -10, 40)
    assert _beyond_range(est, -10, 60)  # past P90
    assert _beyond_range(est, -30, 10)  # below P10
    assert not _beyond_range(est, None, None)

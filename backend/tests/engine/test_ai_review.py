"""Parameter set v12: extra review of AI-written code, and model error by project size."""

from collections.abc import Callable
from decimal import Decimal

import pytest

from app.services.engine.components import AI_REVIEW_KEY, base_effort
from app.services.engine.context import PricingContext
from app.services.engine.core import calculate
from app.services.engine.inputs import EstimateInput
from app.services.seeding.reference import ReferenceData
from tests.engine.conftest import answer, tweak

D = Decimal


@pytest.fixture
def priced(
    golden: Callable[[str], EstimateInput], reference: ReferenceData
) -> Callable[..., EstimateInput]:
    """The small golden project on the v12 India reference data, with the given answers."""

    def make(version: str = "v12", **answers: object) -> EstimateInput:
        inp = tweak(
            golden("small"),
            taxonomy=reference.taxonomy,
            catalog=reference.catalog_version("v5"),  # before source eras (v6)
            rate_card=reference.rate_card("v4"),
            parameters=reference.parameter_set(version),
        )
        for key, value in answers.items():
            inp = answer(inp, key, value)
        return inp

    return make


def test_ai_review_pays_back_part_of_the_saving(priced: Callable[..., EstimateInput]) -> None:
    inp = priced(team_ai_maturity="medium")
    result = calculate(inp)
    review = next(ln for ln in result.lines if ln.line_key == AI_REVIEW_KEY)
    assert review.formula_id == "build.ai_code_review.v1" and review.bucket == "build.testing"
    manual = answer(inp, "team_ai_maturity", "none")
    saved = sum(
        (base_effort(PricingContext(manual), c).effort_pd for c in inp.components), D(0)
    ) - sum((base_effort(PricingContext(inp), c).effort_pd for c in inp.components), D(0))
    share = inp.parameters.ai_productivity.review_share_of_saved
    assert share is not None and saved > 0
    pd = sum(review.role_pd.values(), D(0))
    expected = share * saved * result.timeline.compression_multiplier
    assert abs(pd - expected) < D("0.000001")
    assert list(review.role_pd) == [inp.parameters.ai_productivity.review_role]


def test_no_review_line_without_ai_or_before_v12(priced: Callable[..., EstimateInput]) -> None:
    for inp in (priced(team_ai_maturity="none"), priced("v11", team_ai_maturity="medium")):
        assert AI_REVIEW_KEY not in {ln.line_key for ln in calculate(inp).lines}


def test_model_error_follows_project_size(priced: Callable[..., EstimateInput]) -> None:
    small = calculate(priced(project_size="small"))
    large = calculate(priced(project_size="large"))
    assert small.calibration.model_spread and large.calibration.model_spread
    assert small.calibration.model_spread.name == "model error (small projects, back-tested)"
    assert large.calibration.model_spread.up > small.calibration.model_spread.up
    # the same client type is never priced differently: segment spreads are equal in v12
    gov = calculate(priced(buyer_segment="government"))
    startup = calculate(priced(buyer_segment="small_business"))
    assert gov.totals and startup.totals and gov.totals.p50_paise == startup.totals.p50_paise

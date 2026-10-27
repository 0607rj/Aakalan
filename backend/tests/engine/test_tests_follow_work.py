"""Testing follows the work on small projects (parameter sets v28+, OPEN_QUESTIONS 180): the
tests task is at most tests_max_share_by_size of the tested work on the listed project sizes."""

from collections.abc import Callable
from decimal import Decimal

from app.services.engine.components import effort_plan
from app.services.engine.context import PricingContext
from app.services.engine.core import calculate
from app.services.engine.inputs import EstimateInput
from app.services.engine.reference import TaskType
from app.services.seeding.reference import ReferenceData
from tests.engine.conftest import answer, tweak


def small(
    golden: Callable[[str], EstimateInput], reference: ReferenceData, params: str, size: str
) -> EstimateInput:
    inp = tweak(
        golden("small"),
        taxonomy=reference.taxonomy,
        catalog=reference.catalog_version("v5"),
        rate_card=reference.rate_card("v11"),
        parameters=reference.parameter_set(params),
    )
    return answer(inp, "project_size", size)


def qa_paise(inp: EstimateInput) -> int:
    return sum(ln.likely_paise for ln in calculate(inp).lines if ln.bucket == "build.testing")


def test_tests_are_capped_on_small_projects(
    golden: Callable[[str], EstimateInput], reference: ReferenceData
) -> None:
    inp = small(golden, reference, "v28", "small")
    plan = effort_plan(PricingContext(inp))
    assert plan.tests_scale < 1
    share = Decimal("0.40")
    assert plan.tests_pd * plan.tests_scale == share * plan.tested_pd
    assert qa_paise(inp) < qa_paise(small(golden, reference, "v27", "small"))
    line = next(ln for ln in calculate(inp).lines if ln.bucket == "build.testing")
    assert any(s.label == f"cap {TaskType.TESTS.value}" for s in line.trace.steps)


def test_medium_projects_are_unchanged(
    golden: Callable[[str], EstimateInput], reference: ReferenceData
) -> None:
    before = calculate(small(golden, reference, "v27", "medium")).totals
    after = calculate(small(golden, reference, "v28", "medium")).totals
    assert before is not None and after is not None
    assert after.p50_paise == before.p50_paise
    plan = effort_plan(PricingContext(small(golden, reference, "v28", "medium")))
    assert plan.tests_scale == 1


def test_tested_work_leaves_out_the_tests(
    golden: Callable[[str], EstimateInput], reference: ReferenceData
) -> None:
    inp = small(golden, reference, "v28", "small")
    plan = effort_plan(PricingContext(inp))
    assert plan.tested_pd > 0  # before AI savings, without the tests themselves

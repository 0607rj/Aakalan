"""Parameter set v20 (OPEN_QUESTIONS 144): review and tests follow the reuse, effort caps on
review, pre-build and the architect, the AI review split like other review work, SSL and the
web address the client provides, and lines that follow the build kept out of the range drivers.
Hand-computed on the v1 seed values where the numbers allow it."""

from collections.abc import Callable, Mapping
from decimal import Decimal

import pytest

from app.services.engine.components import (
    AI_KEPT_KEY,
    AI_REVIEW_KEY,
    base_effort,
    component_line,
    effort_plan,
)
from app.services.engine.context import PricingContext
from app.services.engine.core import calculate
from app.services.engine.inputs import EstimateInput
from app.services.engine.reference import EffortCaps, Reuse, TaskType
from app.services.seeding.reference import ReferenceData
from tests.engine.conftest import answer, tweak
from tests.engine.test_formulas import PLAIN_NFR, REG_S, minimal

D = Decimal
BASE_TASKS = [TaskType.CRUD, TaskType.UI_DESIGN, TaskType.TESTS]
EPS = D("0.000000001")


@pytest.fixture
def small(golden: Callable[[str], EstimateInput]) -> EstimateInput:
    return golden("small")


def with_reuse(inp: EstimateInput, **extra: object) -> EstimateInput:
    """CMS build: crud and screens at half effort, review and tests following the reuse."""
    reuse = Reuse(
        source="test",
        tasks=[TaskType.CRUD, TaskType.UI_DESIGN],
        factor_by_build_type={"cms": D("0.5")},
        follow_tasks=[TaskType.REVIEW_UAT, TaskType.TESTS],
        **extra,  # type: ignore[arg-type]
    )
    inp = answer(inp, "build_type", "cms")
    return inp.model_copy(update={"parameters": inp.parameters.model_copy(update={"reuse": reuse})})


def with_caps(inp: EstimateInput, **values: object) -> EstimateInput:
    fields: dict[str, object] = {
        "source": "test",
        "base_tasks": BASE_TASKS,
        "review_task": TaskType.REVIEW_UAT,
        "review_max_share": D(100),
        "pre_build_max_share": D(100),
        "architecture_task": TaskType.ARCHITECTURE,
        "architecture_base_pd": D(100000),
        "architecture_pd_per_hard_problem": D(0),
        **values,
    }
    caps = EffortCaps.model_validate(fields)
    return inp.model_copy(
        update={"parameters": inp.parameters.model_copy(update={"effort_caps": caps})}
    )


def effort(inp: EstimateInput, index: int = 0) -> Decimal:
    return base_effort(PricingContext(inp), inp.components[index]).effort_pd


# --- review and tests follow the reuse ---------------------------------------------------------


def test_review_and_tests_shrink_with_the_work_they_check(small: EstimateInput) -> None:
    """registration_empanelment S before AI savings: crud 36, ui 3, docs 3 (work 42 pd), tests
    12, review 6. CMS halves crud and ui: work 18 + 1.5 + 3 = 22.5 pd, so tests and review
    follow at 22.5 / 42. After AI savings (crud 18 → 9, ui 2.1 → 1.05, docs 1.2, tests 7.2,
    review 5.7): 11.25 + 12.9 × 22.5 / 42 ≈ 18.1607 pd (was 24.15 without)."""
    inp = with_reuse(minimal(small, REG_S, **PLAIN_NFR))
    expected = D("11.25") + D("12.9") * D("22.5") / D(42)
    assert abs(effort(inp) - expected) < EPS
    ctx = PricingContext(inp)
    line = component_line(ctx, base_effort(ctx, inp.components[0]), D(1))
    assert line.formula_id == "component_labour.v5"
    follow = next(s for s in line.trace.steps if s.label == "M_follow")
    assert abs(follow.value - D("22.5") / D(42)) < EPS


def test_nothing_reused_nothing_follows(small: EstimateInput) -> None:
    custom = answer(with_reuse(minimal(small, REG_S, **PLAIN_NFR)), "build_type", "custom")
    assert effort(custom) == D("34.2")


def test_whole_system_testing_follows_the_project_ratio(small: EstimateInput) -> None:
    """A project-wide testing block has no work of its own to reuse: it follows the project's
    build work after reuse / before (here registration's 22.5 / 42)."""
    comps = [*REG_S, {"id": "t", "catalog_key": "functional_testing_uat_support", "size": "S"}]
    plain = with_reuse(minimal(small, comps, **PLAIN_NFR))
    wide = with_reuse(
        minimal(small, comps, **PLAIN_NFR),
        project_wide_components=["functional_testing_uat_support"],
    )
    ratio = effort_plan(PricingContext(wide)).project_reuse_ratio
    assert abs(ratio - D("22.5") / D(42)) < EPS
    assert effort(wide, 1) < effort(plain, 1)


# --- effort caps -----------------------------------------------------------------------------


def test_review_capped_at_a_share_of_the_build(small: EstimateInput) -> None:
    """After AI savings, base (crud 18 + ui 2.1 + tests 7.2) = 27.3 pd; review 5.7 pd capped
    at 0.15 × 27.3 = 4.095 pd: 34.2 − 5.7 + 4.095 = 32.595 pd."""
    inp = with_caps(minimal(small, REG_S, **PLAIN_NFR), review_max_share=D("0.15"))
    assert effort(inp) == D("32.595")
    ctx = PricingContext(inp)
    line = component_line(ctx, base_effort(ctx, inp.components[0]), D(1))
    assert any(s.label == "cap review_uat" for s in line.trace.steps)
    loose = with_caps(minimal(small, REG_S, **PLAIN_NFR), review_max_share=D("0.25"))
    assert effort(loose) == D("34.2")  # 0.25 × 27.3 = 6.825 pd ≥ 5.7: not capped


def test_pre_build_capped_at_a_share_of_the_build(small: EstimateInput) -> None:
    """solution_architecture is all pre-build: capped at 0.15 × 27.3 = 4.095 pd."""
    comps = [*REG_S, {"id": "a", "catalog_key": "solution_architecture", "size": "S"}]
    inp = with_caps(minimal(small, comps, **PLAIN_NFR), pre_build_max_share=D("0.15"))
    assert abs(effort(inp, 1) - D("4.095")) < EPS
    assert effort(inp, 0) == D("34.2")  # build work is never capped by pre-build


def test_architect_capped_unless_hard_problems_need_more(small: EstimateInput) -> None:
    """security_hardening L: architecture 120 × 0.2 = 24 pd; the cap is 3 pd plus 4 pd per hard
    problem, so 3 pd for a plain project and 7 pd with one hard problem."""
    comps = [*REG_S, {"id": "h", "catalog_key": "security_hardening", "size": "L"}]
    free = minimal(small, comps, **PLAIN_NFR)
    capped = with_caps(free, architecture_base_pd=D(3), architecture_pd_per_hard_problem=D(4))
    arch = effort_plan(PricingContext(capped)).architecture_pd
    assert arch > D(7)
    assert abs(effort(capped, 1) - (effort(free, 1) - arch + D(3))) < EPS
    hard_comps: list[Mapping[str, object]] = [comps[0], {**comps[1], "hard_problem": True}]
    hard = with_caps(
        minimal(small, hard_comps, **PLAIN_NFR),
        architecture_base_pd=D(3),
        architecture_pd_per_hard_problem=D(4),
    )
    assert abs(effort(hard, 1) - (effort(free, 1) - arch + D(7))) < EPS


def test_no_build_work_no_caps(small: EstimateInput) -> None:
    only_pre = [{"id": "a", "catalog_key": "solution_architecture", "size": "S"}]
    free = minimal(small, only_pre, **PLAIN_NFR)
    capped = with_caps(free, pre_build_max_share=D("0.15"), architecture_base_pd=D(3))
    assert effort(capped) == effort(free)


def test_capped_tasks_cannot_be_their_own_base() -> None:
    with pytest.raises(ValueError):
        EffortCaps(
            source="test",
            base_tasks=[TaskType.CRUD, TaskType.REVIEW_UAT],
            review_task=TaskType.REVIEW_UAT,
            review_max_share=D("0.15"),
            pre_build_max_share=D("0.15"),
            architecture_task=TaskType.ARCHITECTURE,
            architecture_base_pd=D(3),
            architecture_pd_per_hard_problem=D(4),
        )


# --- on the v20 reference data -----------------------------------------------------------------


@pytest.fixture
def v20(golden: Callable[[str], EstimateInput], reference: ReferenceData) -> EstimateInput:
    """The small golden project on parameters v20 and rate card v9."""
    return tweak(
        golden("small"),
        taxonomy=reference.taxonomy,
        catalog=reference.catalog_version("v5"),
        rate_card=reference.rate_card("v9"),
        parameters=reference.parameter_set("v20"),
    )


def test_ai_review_split_like_other_review_work(v20: EstimateInput) -> None:
    inp = answer(v20, "team_ai_maturity", "medium")
    result = calculate(inp)
    review = next(ln for ln in result.lines if ln.line_key == AI_REVIEW_KEY)
    assert review.formula_id == "build.ai_code_review.v2" and review.follows_build
    shares = inp.parameters.task_roles.split[TaskType.REVIEW_UAT]
    total = sum(review.role_pd.values(), D(0))
    assert set(review.role_pd) == set(shares)
    for role, share in shares.items():
        assert abs(review.role_pd[role] - total * share) < EPS
    # the share of saved effort is a placeholder, so the estimate says so
    assert "param:ai_productivity.review_share_of_saved" in result.calibration.placeholder_refs


def test_client_provided_ssl_and_domain_cost_nothing(v20: EstimateInput) -> None:
    def ssl_domain(inp: EstimateInput) -> list[int]:
        return [ln.likely_paise for ln in calculate(inp).lines if ln.bucket == "run.ssl_domain"]

    paid = answer(v20, "ssl_type", "ov")
    assert all(p > 0 for p in ssl_domain(paid))
    provided = answer(answer(paid, "ssl_in_scope", False), "domain_in_scope", False)
    lines = [ln for ln in calculate(provided).lines if ln.bucket == "run.ssl_domain"]
    assert lines and all(ln.likely_paise == 0 for ln in lines)
    assert all(ln.formula_id == "maintenance.ssl_domain.v2" for ln in lines)
    steps = {s.expression for s in lines[0].trace.steps}
    assert "provided by the client" in steps
    # a free (Let's Encrypt) certificate: only the web address is paid
    free = answer(paid, "ssl_type", "dv_free")
    assert sum(ssl_domain(free)) < sum(ssl_domain(paid))


def test_lines_that_follow_the_build_are_not_range_drivers(v20: EstimateInput) -> None:
    """Project management is a share of the build: its spread is the build's, so naming it as
    a source of uncertainty double counts (and ranked it first on small projects)."""
    result = calculate(answer(v20, "team_ai_maturity", "medium"))
    pm = [ln for ln in result.lines if ln.bucket == "programme.project_management"]
    assert pm and all(ln.follows_build for ln in pm)
    assert "programme.project_management" not in {d.bucket for d in result.top_drivers}


def test_review_is_capped_after_the_reuse_not_cut_twice(small: EstimateInput) -> None:
    """The cap compares review after M_reuse / M_follow with the build after reuse, so a block
    whose review the reuse already shrank is not scaled again by a factor worked out on its
    pre-reuse review. registration S, CMS: review 5.7 × r, base 9 + 1.05 + 7.2 × r (r = 22.5 /
    42); review = min(5.7 × r, share × base)."""
    r = D("22.5") / D(42)
    rest = D("11.25") + D("7.2") * r  # crud, ui, docs and tests after reuse and AI savings
    for share in (D("0.15"), D("0.25")):
        inp = with_caps(with_reuse(minimal(small, REG_S, **PLAIN_NFR)), review_max_share=share)
        plan = effort_plan(PricingContext(inp))
        assert abs(plan.review_pd - D("5.7") * r) < EPS  # measured after the reuse
        review = effort(inp) - rest
        expected = min(D("5.7") * r, share * (D("10.05") + D("7.2") * r))
        assert abs(review - expected) < EPS
    # 0.25: the reuse alone cut it (once); the cap does not bind
    loose = with_caps(with_reuse(minimal(small, REG_S, **PLAIN_NFR)), review_max_share=D("0.25"))
    assert abs(effort(loose) - rest - D("5.7") * r) < EPS


def test_caps_grow_with_project_size(small: EstimateInput) -> None:
    """review ≤ 0.15 × base on a small project (32.595 pd, as the flat cap), ≤ 0.25 on a large
    one (0.25 × 27.3 = 6.825 ≥ 5.7: not capped)."""
    by_size = {"small": D("0.15"), "large": D("0.25")}
    inp = with_caps(
        minimal(small, REG_S, **PLAIN_NFR),
        review_max_share=D("0.15"),
        review_max_share_by_size=by_size,
    )
    assert effort(answer(inp, "project_size", "small")) == D("32.595")
    assert effort(answer(inp, "project_size", "large")) == D("34.2")
    assert effort(answer(inp, "project_size", "medium")) == D("32.595")  # not listed: flat
    ctx = PricingContext(answer(inp, "project_size", "small"))
    line = component_line(ctx, base_effort(ctx, ctx.inp.components[0]), D(1))
    assert any(
        p.path == "effort_caps.review_max_share_by_size.small" for p in line.trace.parameters
    )


def test_ai_saving_kept_as_margin_when_asked(v20: EstimateInput) -> None:
    """The cost lines never change; the share not passed to the client is added as margin."""
    ai = answer(v20, "team_ai_maturity", "medium")
    before = calculate(ai)
    assert AI_KEPT_KEY not in {ln.line_key for ln in before.lines}  # not answered: as before
    passed = calculate(answer(ai, "ai_passthrough_percent", D(1)))
    kept = calculate(answer(ai, "ai_passthrough_percent", D(0)))
    line = next(ln for ln in kept.lines if ln.line_key == AI_KEPT_KEY)
    identified = int(str(line.inputs["ai_saving_identified_paise"]))
    assert identified > 0 and line.likely_paise == identified and line.derived
    assert line.bucket == "commercial.margin"  # hidden from estimators like the margin
    zero = next(ln for ln in passed.lines if ln.line_key == AI_KEPT_KEY)
    assert zero.likely_paise == 0 and zero.inputs["ai_saving_identified_paise"] == identified
    assert passed.totals and before.totals and kept.totals
    assert passed.totals.p50_paise == before.totals.p50_paise
    costs = {ln.line_key: ln.likely_paise for ln in before.lines if ln.stage != "commercial"}
    assert {ln.line_key: ln.likely_paise for ln in kept.lines if ln.stage != "commercial"} == costs
    added = kept.totals.likely_paise - before.totals.likely_paise  # with GST at the margin's rate
    assert abs(added - identified * (1 + line.gst_percent)) <= 2
    # the simulated price moves by the same fixed amount (the runs add up paise)
    moved = kept.totals.p50_paise - before.totals.p50_paise
    assert abs(moved - identified * (1 + line.gst_percent)) <= 2
    half = calculate(answer(ai, "ai_passthrough_percent", D("0.5")))
    half_line = next(ln for ln in half.lines if ln.line_key == AI_KEPT_KEY)
    assert abs(half_line.likely_paise - identified / 2) <= 1


def test_architect_cap_grows_with_project_size(small: EstimateInput) -> None:
    """architect ≤ max(base days, share[size] × build) + 4 per hard problem; a size that is
    not listed keeps the base days (OPEN_QUESTIONS 148)."""
    comps = [*REG_S, {"id": "h", "catalog_key": "security_hardening", "size": "L"}]
    inp = with_caps(
        minimal(small, comps, **PLAIN_NFR),
        architecture_base_pd=D(3),
        architecture_pd_per_hard_problem=D(4),
        architecture_max_share_by_size={"small": D("0.01"), "large": D("0.2")},
    )
    large = effort_plan(PricingContext(answer(inp, "project_size", "large")))
    assert large.architecture_cap_pd == max(D(3), D("0.2") * large.base_pd) > D(3)
    small_plan = effort_plan(PricingContext(answer(inp, "project_size", "small")))
    assert small_plan.architecture_cap_pd == D(3)  # 1% of the build is under the base days
    medium = effort_plan(PricingContext(answer(inp, "project_size", "medium")))
    assert medium.architecture_cap_pd == D(3)  # not listed
    ctx = PricingContext(answer(inp, "project_size", "large"))
    line = component_line(ctx, base_effort(ctx, ctx.inp.components[1]), D(1))
    if large.architecture_scale < 1:
        assert any(
            p.path == "effort_caps.architecture_max_share_by_size.large"
            for p in line.trace.parameters
        )

"""Unit tests for engine formulas and multipliers, with hand-computed expectations from the
v1 seed values (brief Section 13)."""

from collections.abc import Callable, Mapping, Sequence
from decimal import Decimal

import numpy as np
import pytest

from app.services.engine.commercial import BaseSums, Factors, derived_amounts
from app.services.engine.components import base_effort, component_line, nfr_multiplier
from app.services.engine.context import PricingContext
from app.services.engine.core import calculate
from app.services.engine.inputs import EstimateInput
from app.services.engine.money import interpolate, to_paise
from app.services.engine.reference import Point
from app.services.engine.simulation import group_quantiles, triangular_inverse
from app.services.engine.timeline import compression_multiplier, natural_duration
from app.services.hosting.sizing import size
from tests.engine.conftest import answer, tweak

D = Decimal


def minimal(
    inp: EstimateInput, components: Sequence[Mapping[str, object]], **answers: object
) -> EstimateInput:
    """The small golden input reduced to the given components and answers."""
    out = tweak(inp, components=components, answers=[], requirements=inp.requirements)
    for key, value in answers.items():
        out = answer(out, key, value)
    return out


@pytest.fixture
def small(golden: Callable[[str], EstimateInput]) -> EstimateInput:
    return golden("small")


# --- money ------------------------------------------------------------------------------------


def test_to_paise_rounds_half_up() -> None:
    assert to_paise(D("1.005")) == 101
    assert to_paise(D("1.004")) == 100
    assert to_paise(D("0")) == 0


def test_interpolate_clamps_and_extrapolates() -> None:
    pts = [Point(x=D("0.6"), y=D("1.4")), Point(x=D("1.0"), y=D("1.0"))]
    assert interpolate(pts, D("0.8")) == D("1.2")
    assert interpolate(pts, D("0.5")) == D("1.4")
    assert interpolate(pts, D("0.55"), extrapolate=True) == D("1.45")
    assert interpolate(pts, D("2")) == D("1.0")


# --- component labour (brief 7.1) ------------------------------------------------------------


def test_component_labour_hand_computed(small: EstimateInput) -> None:
    """registration_empanelment, size S (60 pd), medium complexity, NFR multipliers all 1:
    crud 60×.6×(1−.5)=18 pd×7000 + tests 60×.2×(1−.4)=7.2×6000 + ui 60×.05×.7=2.1×9000
    + docs 60×.05×.4=1.2×5500 + review 60×.1×.95=5.7×10000 = ₹2,51,700."""
    inp = minimal(
        small,
        [{"id": "c", "catalog_key": "registration_empanelment", "size": "S"}],
        languages=1,
        gigw_accessibility=False,
        peak_concurrent_users=100,
    )
    ctx = PricingContext(inp)
    effort = base_effort(ctx, inp.components[0])
    assert effort.effort_pd == D("34.2")
    line = component_line(ctx, effort, D(1))
    assert line.likely_paise == 251_700_00
    assert line.role_pd["role.developer"] == D("18")
    assert line.trace.component is not None
    assert len(line.trace.steps) >= 5


def test_complexity_and_licence_factors(small: EstimateInput) -> None:
    comp = [{"id": "c", "catalog_key": "workflow_engine", "size": "M", "complexity": "high"}]
    base = minimal(small, comp)
    ctx = PricingContext(base)
    medium = minimal(small, [{**comp[0], "complexity": "medium"}])
    e_high = base_effort(ctx, base.components[0]).effort_pd
    e_med = base_effort(PricingContext(medium), medium.components[0]).effort_pd
    assert e_high == e_med * D("1.5")
    licensed = answer(medium, "licensing", "licensed")
    e_lic = base_effort(PricingContext(licensed), licensed.components[0]).effort_pd
    assert e_lic == e_med * D("0.6")


def test_nfr_multiplier_languages_capped(small: EstimateInput) -> None:
    comp = [{"id": "c", "catalog_key": "documentation_manuals", "size": "S"}]
    three = PricingContext(minimal(small, comp, languages=3))
    t = three.builder(
        line_key="x",
        stage="build",
        bucket="build.documentation",
        year=0,
        label="",
        formula_id="component_labour.v1",
    )
    assert nfr_multiplier(t, three.inp.catalog.get("documentation_manuals")) == D("1.08")
    many = PricingContext(minimal(small, comp, languages=22))
    t = many.builder(
        line_key="x",
        stage="build",
        bucket="build.documentation",
        year=0,
        label="",
        formula_id="component_labour.v1",
    )
    assert nfr_multiplier(t, many.inp.catalog.get("documentation_manuals")) == D("1.4")


def test_ai_maturity_scales_savings(small: EstimateInput) -> None:
    comp = [{"id": "c", "catalog_key": "notifications", "size": "M"}]
    low = minimal(small, comp, team_ai_maturity="low")
    high = minimal(small, comp, team_ai_maturity="high")
    e_low = base_effort(PricingContext(low), low.components[0]).effort_pd
    e_high = base_effort(PricingContext(high), high.components[0]).effort_pd
    assert e_low > e_high


# --- timeline (brief 7.3) -------------------------------------------------------------------


def test_compression_curve(small: EstimateInput) -> None:
    ctx = PricingContext(small)
    assert compression_multiplier(ctx, D("1.2")) == D(1)
    assert compression_multiplier(ctx, D("0.8")) == D("1.2")
    assert compression_multiplier(ctx, D("0.6")) == D("1.4")
    assert compression_multiplier(ctx, D("0.55")) == D("1.45")


def test_natural_duration_never_decreases_with_effort(small: EstimateInput) -> None:
    ctx = PricingContext(small)
    months = [natural_duration(ctx, D(pd)).months for pd in range(0, 20000, 50)]
    assert months == sorted(months)
    assert months[0] == small.parameters.timeline.min_duration_months


def test_deadline_below_floor_is_not_feasible(small: EstimateInput) -> None:
    natural = calculate(small).timeline.natural_duration_months
    result = calculate(answer(small, "deadline_months", str(natural * D("0.4"))))
    assert not result.feasible and result.totals is None and not result.lines
    assert result.infeasibility is not None
    phased = [cid for p in result.infeasibility.phases for cid in p.component_instance_ids]
    assert sorted(phased) == sorted(c.id for c in small.components)
    assert len(result.infeasibility.phases) >= 2


def test_extended_deadline_adds_programme_overhead(small: EstimateInput) -> None:
    natural = calculate(small)
    extended = calculate(
        answer(small, "deadline_months", str(natural.timeline.natural_duration_months * 2))
    )
    assert extended.timeline.status == "extended"
    assert extended.totals is not None and natural.totals is not None
    prog = {g.key: g.likely_paise for g in natural.by_stage}["programme"]
    prog_ext = {g.key: g.likely_paise for g in extended.by_stage}["programme"]
    build = {g.key: g.likely_paise for g in natural.by_stage}["build"]
    build_ext = {g.key: g.likely_paise for g in extended.by_stage}["build"]
    assert prog_ext > prog and build_ext == build


# --- hosting and run costs (brief 7.4) -------------------------------------------------------


@pytest.mark.parametrize(
    ("sla", "pattern"), [("99.0", "single"), ("99.5", "ha"), ("99.9", "ha"), ("99.95", "ha_dr")]
)
def test_hosting_pattern_by_sla(small: EstimateInput, sla: str, pattern: str) -> None:
    ctx = PricingContext(answer(small, "uptime_sla", sla))
    t = ctx.builder(
        line_key="x",
        stage="run",
        bucket="run.hosting",
        year=1,
        label="",
        formula_id="hosting.compute.v1",
    )
    assert size(t).pattern == pattern


def test_app_servers_scale_with_concurrency(small: EstimateInput) -> None:
    ctx = PricingContext(answer(answer(small, "peak_concurrent_users", 2000), "uptime_sla", "99.5"))
    t = ctx.builder(
        line_key="x",
        stage="run",
        bucket="run.hosting",
        year=1,
        label="",
        formula_id="hosting.compute.v1",
    )
    plan = size(t)
    assert plan.app_servers == 20  # ceil(ceil(2000/25)/4)
    assert plan.db_tier == "large"


def test_dr_lines_only_for_ha_dr(small: EstimateInput) -> None:
    single = calculate(answer(small, "uptime_sla", "99.0"))
    dr = calculate(answer(small, "uptime_sla", "99.95"))
    assert not [ln for ln in single.lines if ln.bucket == "run.dr"]
    assert len([ln for ln in dr.lines if ln.bucket == "run.dr"]) == 3


def test_ai_runtime_api_hand_computed(small: EstimateInput) -> None:
    """1000 q/day × 365 × (2000 × $3 + 400 × $15)/1e6 × ₹88 × 1.03 = ₹3,97,003.20 (year 1)."""
    inp = answer(answer(small, "chatbot_queries_per_day", 1000), "ai_runtime_mode", "api")
    line = next(ln for ln in calculate(inp).lines if ln.line_key == "run.ai_runtime/llm_api/y1")
    assert line.likely_paise == 397_003_20


def test_self_hosted_gpu_and_on_prem_scenarios(small: EstimateInput) -> None:
    gpu = calculate(answer(small, "ai_runtime_mode", "self_hosted_gpu"))
    assert any(ln.formula_id == "ai_runtime.gpu.v1" for ln in gpu.lines)
    onprem = calculate(answer(small, "hosting_provider", "on_prem"))
    capex = [ln for ln in onprem.lines if ln.bucket == "go_live.infrastructure_procurement"]
    assert len(capex) == 1 and capex[0].year == 0
    assert not any(ln.formula_id == "hosting.compute.v1" for ln in onprem.lines)


def test_escalation_applies_per_year(small: EstimateInput) -> None:
    lines = {ln.line_key: ln for ln in calculate(small).lines}
    y1 = lines["run.ssl_domain/ssl_domain/y1"].likely_paise
    y2 = lines["run.ssl_domain/ssl_domain/y2"].likely_paise
    assert y1 == to_paise(D("26500") * D("1.08"))
    assert y2 == to_paise(D("26500") * D("1.08") ** 2)


def test_licences_only_when_licensed(small: EstimateInput) -> None:
    assert not [ln for ln in calculate(small).lines if ln.bucket == "run.licences"]
    licensed = calculate(answer(small, "licensing", "licensed"))
    keys = {ln.trace.rate_items[0].key for ln in licensed.lines if ln.bucket == "run.licences"}
    assert keys == {"licence.bpm_suite.year", "licence.chatbot_platform.year"}


def test_maintenance_rule_of_thumb_check_present(small: EstimateInput) -> None:
    checks = calculate(small).sanity_checks
    assert checks and checks[0].key == "maintenance_rule_of_thumb"


# --- commercial (brief 7.5) ------------------------------------------------------------------


def test_derived_amounts_formula() -> None:
    sums = BaseSums(total=D(1000), build=D(600), run=D(400), by_gst_rate={D("0.18"): D(1000)})
    f = Factors(
        contingency=D("0.1"), working_capital=D("0.01"), pbg=D("0.001"), ld_build=D("0.01"),
        penalty_run=D("0.02"), margin=D("0.15"), gst_contingency=D("0.18"),
        gst_working_capital=D("0.18"), gst_pbg=D("0.18"), gst_penalty_reserve=D("0.18"),
        gst_margin=D("0.18"),
    )  # fmt: skip
    out = derived_amounts(sums, f, lambda r: r)
    assert out["contingency"] == D(100)
    assert out["working_capital"] == D(6)
    assert out["pbg"] == D("1.1")
    assert out["penalty_reserve"] == D(14)
    assert out["margin"] == D("0.15") * D("1121.1")
    pre_gst = D(1000) + sum(v for k, v in out.items() if k != "gst")
    assert out["gst"] == D("0.18") * pre_gst


def test_margin_and_gst_follow_answers(small: EstimateInput) -> None:
    base = {ln.line_key: ln for ln in calculate(small).lines}
    no_margin = {ln.line_key: ln for ln in calculate(answer(small, "margin_percent", 0)).lines}
    assert no_margin["commercial.margin/total"].likely_paise == 0
    assert base["commercial.margin/total"].likely_paise > 0
    zero_gst = {ln.line_key: ln for ln in calculate(answer(small, "gst_percent", 0)).lines}
    assert zero_gst["commercial.gst/total"].likely_paise == 0


def test_contingency_from_clarity(small: EstimateInput) -> None:
    vague = tweak(
        small, requirements=[{**r.model_dump(), "clarity_score": 1} for r in small.requirements]
    )
    clear = tweak(
        small, requirements=[{**r.model_dump(), "clarity_score": 5} for r in small.requirements]
    )
    c_vague = next(ln for ln in calculate(vague).lines if ln.bucket == "commercial.contingency")
    c_clear = next(ln for ln in calculate(clear).lines if ln.bucket == "commercial.contingency")
    assert c_vague.trace.steps[0].value == D("0.15")
    assert c_clear.trace.steps[0].value == D("0.05")


def test_defaults_are_listed_as_assumptions(small: EstimateInput) -> None:
    result = calculate(small)
    keys = {a.key for a in result.assumptions}
    assert "hosting_provider" in keys  # not answered in the small golden
    assert "users_total" not in keys  # answered


# --- simulation (brief 7.2) ------------------------------------------------------------------


def test_triangular_inverse_endpoints() -> None:
    u = np.array([0.0, 0.25, 1.0])
    x = triangular_inverse(u, 10.0, 20.0, 50.0)
    assert x[0] == pytest.approx(10.0) and x[2] == pytest.approx(50.0)
    assert triangular_inverse(np.array([0.5]), 5.0, 5.0, 5.0)[0] == 5.0


def test_group_quantiles_are_seeded_and_independent() -> None:
    a = group_quantiles(1, "build|x", 100)
    assert np.array_equal(a, group_quantiles(1, "build|x", 100))
    assert not np.array_equal(a, group_quantiles(1, "build|y", 100))
    assert not np.array_equal(a, group_quantiles(2, "build|x", 100))


def test_top_drivers_and_confidence(golden: Callable[[str], EstimateInput]) -> None:
    result = calculate(golden("medium"))
    assert len(result.top_drivers) == 3
    shares = [d.variance_share for d in result.top_drivers]
    assert shares == sorted(shares, reverse=True)
    assert result.top_drivers_text.endswith("contribute most of the range.")
    assert result.confidence.label in {"high", "medium", "low"}
    assert result.totals is not None
    t = result.totals
    assert t.p10_paise <= t.p50_paise <= t.p90_paise
    assert t.low_sum_paise <= t.likely_paise <= t.high_sum_paise

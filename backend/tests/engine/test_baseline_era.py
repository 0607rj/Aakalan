"""Catalog v6 source eras: the team's AI savings are applied once to pre-AI effort data, never
to AI-assisted data, and to unknown-era data only in the separate pre-AI sensitivity run."""

from collections.abc import Callable
from decimal import Decimal

import pytest

from app.services.engine.components import AI_REVIEW_KEY
from app.services.engine.core import calculate
from app.services.engine.inputs import EstimateInput
from app.services.engine.outputs import EstimateResult
from app.services.engine.reference import Catalog
from app.services.estimates.service import era_sensitivity
from app.services.seeding.reference import ReferenceData
from tests.engine.conftest import answer, tweak

BASIS = {
    "pre_ai": "date_heuristic",
    "ai_assisted": "explicit_statement",
    "unknown": "not_established",
}
MATURITIES = ("none", "low", "medium", "high")


def with_era(catalog: Catalog, era: str | None) -> Catalog:
    """Every component with one evidence item of this era (None: no provenance, as v1-v5)."""
    components = []
    for c in catalog.components:
        data = c.model_dump()
        if era is None:
            data.update(source_era=None, era_reason="", confidence=None, evidence=[])
        else:
            data.update(
                source_era=era,
                evidence=[
                    {
                        "id": f"{c.key}.test",
                        "citation": "test source",
                        "source_type": "measured_projects",
                        "published": 2020 if era == "pre_ai" else None,
                        "era": era,
                        "era_basis": BASIS[era],
                        "ai_workflow": "AI pair programming" if era == "ai_assisted" else None,
                        "quality": "medium",
                    }
                ],
            )
        components.append(data)
    return Catalog.model_validate({"version": catalog.version, "components": components})


@pytest.fixture
def priced(
    golden: Callable[[str], EstimateInput], reference: ReferenceData
) -> Callable[..., EstimateInput]:
    """The small golden project on current India reference data, every component given `era`
    ("real" = catalog v6 as published)."""

    def make(era: str | None, maturity: str = "medium", **update: object) -> EstimateInput:
        v6 = reference.catalog_version("v6")
        inp = tweak(
            golden("small"),
            taxonomy=reference.taxonomy,
            catalog=v6 if era == "real" else with_era(v6, era),
            rate_card=reference.rate_card("v5"),
            parameters=reference.parameter_set("v15"),
            monte_carlo_runs=500,
            **update,
        )
        return answer(inp, "team_ai_maturity", maturity)

    return make


def effort(inp: EstimateInput) -> Decimal:
    return calculate(inp).timeline.build_effort_pd


def review(result: EstimateResult) -> Decimal | None:
    """AI-saved person-days the review-of-AI-code line was priced on (None: no line)."""
    line = next((ln for ln in result.lines if ln.line_key == AI_REVIEW_KEY), None)
    return Decimal(str(line.inputs["ai_saved_pd"])) if line else None


@pytest.mark.parametrize("maturity", MATURITIES)
def test_ai_assisted_data_gets_no_ai_discount(
    priced: Callable[..., EstimateInput], maturity: str
) -> None:
    without_ai = effort(priced(None, "none"))
    inp = priced("ai_assisted", maturity)
    result = calculate(inp)
    assert result.timeline.build_effort_pd == without_ai
    assert review(result) is None  # no saving, so no review of AI-written code either
    sensitivity = inp.model_copy(update={"era_scenario": "pre_ai_sensitivity"})
    assert effort(sensitivity) == without_ai  # not even in the sensitivity run
    assert era_sensitivity(inp, result) is None


def test_pre_ai_data_gets_the_saving_exactly_once(priced: Callable[..., EstimateInput]) -> None:
    legacy = calculate(priced(None))
    result = calculate(priced("pre_ai"))
    assert result.timeline.build_effort_pd == legacy.timeline.build_effort_pd  # today's formula
    assert result.totals == legacy.totals
    saved = effort(priced("pre_ai", "none")) - result.timeline.build_effort_pd
    assert saved > 0
    assert review(result) == saved  # the review is priced on the saving actually applied
    again = calculate(priced("pre_ai", era_scenario="pre_ai_sensitivity"))
    assert again.totals == result.totals  # never applied a second time
    assert [ln.likely_paise for ln in again.lines] == [ln.likely_paise for ln in result.lines]


def test_unknown_era_has_no_saving_in_the_estimate(priced: Callable[..., EstimateInput]) -> None:
    inp = priced("unknown")
    result = calculate(inp)
    assert result.timeline.build_effort_pd == effort(priced(None, "none"))
    assert review(result) is None
    line = next(ln for ln in result.lines if ln.trace.component is not None)
    component = line.trace.component
    assert component is not None and line.formula_id == "component_labour.v3"
    assert line.inputs["source_era"] == "unknown" and line.inputs["ai_saving"] == "not applied"
    assert line.inputs["evidence"] == [f"{component.catalog_key}.test"]

    pre_ai = calculate(inp.model_copy(update={"era_scenario": "pre_ai_sensitivity"}))
    as_pre_ai = calculate(priced("pre_ai"))
    assert pre_ai.timeline.build_effort_pd == as_pre_ai.timeline.build_effort_pd
    assert review(pre_ai) == review(as_pre_ai)  # review only where the saving is applied
    assert pre_ai.totals == as_pre_ai.totals
    assert result.timeline.build_effort_pd > pre_ai.timeline.build_effort_pd


def test_catalogs_without_eras_price_as_before(priced: Callable[..., EstimateInput]) -> None:
    result = calculate(priced(None))
    labour = [ln for ln in result.lines if ln.trace.component is not None]
    assert labour and {ln.formula_id for ln in labour} == {"component_labour.v2"}
    assert all("source_era" not in ln.inputs for ln in labour)


def test_published_v6_reviews_only_the_pre_ai_blocks(
    priced: Callable[..., EstimateInput], reference: ReferenceData
) -> None:
    """Catalog v6: documentation_manuals is pre_ai (provisional), the rest of the small project
    is unknown, so the AI saving (and its review) comes from that block alone."""
    v6 = reference.catalog_version("v6")
    inp = priced("real")
    pre_ai = [c.id for c in inp.components if v6.get(c.catalog_key).source_era == "pre_ai"]
    assert pre_ai == ["S-C11"]  # documentation_manuals; the other ten blocks are unknown
    result = calculate(inp)
    saved = effort(answer(inp, "team_ai_maturity", "none")) - result.timeline.build_effort_pd
    assert saved > 0 and review(result) == saved
    for ln in result.lines:
        if ln.trace.component is not None:
            applied = "applied" if ln.component_instance_id == "S-C11" else "not applied"
            assert ln.inputs["ai_saving"] == applied, ln.line_key


def test_sensitivity_range_keeps_the_estimate(priced: Callable[..., EstimateInput]) -> None:
    inp = priced("real")
    result = calculate(inp)
    s = era_sensitivity(inp, result)
    assert s is not None and result.totals is not None
    pre_ai = calculate(inp.model_copy(update={"era_scenario": "pre_ai_sensitivity"})).totals
    assert pre_ai is not None
    assert s["p10_paise"] == pre_ai.p10_paise and s["p50_paise"] == pre_ai.p50_paise
    assert s["range_low_paise"] == min(result.totals.p10_paise, pre_ai.p10_paise)
    assert s["range_high_paise"] == result.totals.p90_paise
    assert pre_ai.p50_paise < result.totals.p50_paise  # the estimate claims no unknown saving
    assert s["range_low_paise"] <= result.totals.p10_paise <= result.totals.p50_paise
    assert (s["unknown_components"], s["components"]) == (10, 11)
    # the second run never changes the estimate itself
    assert calculate(inp).model_dump_json() == result.model_dump_json()


def test_no_sensitivity_without_ai_tools_or_unknown_data(
    priced: Callable[..., EstimateInput],
) -> None:
    for inp in (priced("real", "none"), priced(None), priced("pre_ai")):
        assert era_sensitivity(inp, calculate(inp)) is None

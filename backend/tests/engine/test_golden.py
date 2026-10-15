"""Golden estimates (brief M1 acceptance): identical totals on every run and a full trace for
every cost line. If these fail after an intentional engine/seed change, run `make golden` and
review the diff."""

import json
from collections.abc import Callable

import pytest

from app.services.engine.core import calculate
from app.services.engine.formulas import FORMULAS
from app.services.engine.inputs import EstimateInput
from app.services.seeding.golden import GOLDEN_NAMES, expected_path, summarise


@pytest.mark.parametrize("name", GOLDEN_NAMES)
def test_golden_matches_expected(name: str, golden: Callable[[str], EstimateInput]) -> None:
    expected = json.loads(expected_path(name).read_text(encoding="utf-8"))
    assert summarise(calculate(golden(name))) == expected


@pytest.mark.parametrize("name", GOLDEN_NAMES)
def test_golden_is_reproducible(name: str, golden: Callable[[str], EstimateInput]) -> None:
    first = calculate(golden(name)).model_dump_json()
    second = calculate(EstimateInput.model_validate_json(golden(name).model_dump_json()))
    assert second.model_dump_json() == first


@pytest.mark.parametrize("name", GOLDEN_NAMES)
def test_every_line_has_full_trace(name: str, golden: Callable[[str], EstimateInput]) -> None:
    inp = golden(name)
    result = calculate(inp)
    components = {c.id: c for c in inp.components}
    assert result.lines
    for line in result.lines:
        tr = line.trace
        assert tr.formula_id == line.formula_id and tr.formula == FORMULAS[line.formula_id]
        assert tr.rate_items or tr.parameters or tr.drivers, line.line_key
        assert tr.steps or tr.rate_items, line.line_key
        assert line.low_paise <= line.likely_paise <= line.high_paise, line.line_key
        assert all(r.rate_card_version == inp.rate_card.version for r in tr.rate_items)
        assert all(p.parameter_set_version == inp.parameters.version for p in tr.parameters)
        if line.component_instance_id is not None:
            ci = components[line.component_instance_id]
            assert tr.component is not None and tr.component.catalog_key == ci.catalog_key
            assert {r.id for r in tr.requirements} >= set(ci.requirement_ids)
        for req in tr.requirements:
            assert req.clause_ref and req.page, f"{line.line_key}: {req.code} lacks clause/page"


def test_golden_lines_link_back_to_rfp_clauses(golden: Callable[[str], EstimateInput]) -> None:
    """Driver-based lines (hosting, helpdesk...) reach clauses via cited questionnaire answers."""
    result = calculate(golden("medium"))
    hosting = next(ln for ln in result.lines if ln.line_key == "run.hosting/compute/y1")
    assert {"M-R11"} <= set(hosting.requirement_ids)
    clause = {r.clause_ref for r in hosting.trace.requirements}
    assert "5.1" in clause


def test_placeholders_mark_estimate_uncalibrated(golden: Callable[[str], EstimateInput]) -> None:
    result = calculate(golden("small"))
    assert result.calibration.status == "uncalibrated"
    assert "rate:role.developer" in result.calibration.placeholder_refs
    assert "catalog:registration_empanelment" in result.calibration.placeholder_refs


def test_seed_changes_simulation_only(golden: Callable[[str], EstimateInput]) -> None:
    base = golden("small")
    a = calculate(base)
    b = calculate(base.model_copy(update={"seed": base.seed + 1}))
    assert a.totals is not None and b.totals is not None
    assert a.totals.likely_paise == b.totals.likely_paise
    assert a.totals.p50_paise != b.totals.p50_paise

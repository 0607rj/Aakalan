"""Front end only (parameter sets v31+, OPEN_QUESTIONS 192): only the screens are built over
the client's existing server side and APIs, so the server-side work shrinks, the questions about
servers are hidden and fixed, and a description that says so answers the question."""

from datetime import date
from decimal import Decimal
from typing import Any

from app.core.config import get_settings
from app.services.calibration.backtest import reference_for
from app.services.engine.core import calculate
from app.services.engine.outputs import EstimateResult
from app.services.extraction.describe import suggest_features
from app.services.quick.config import quick_config
from app.services.quick.service import (
    QuickRequest,
    _choice,
    plan_quick,
    plan_to_input,
    standard_blocks,
)
from app.services.seeding.reference import load_reference

CFG = quick_config()
DATA = load_reference(get_settings().seeds_dir)


def request(build_part: str, **choices: Any) -> QuickRequest:
    return QuickRequest(
        name="app rebuild",
        features=["mobile_app", "payments", "search"],
        choices={"platforms": "app", "build_part": build_part, "support_years": 0, **choices},
    )


def price(req: QuickRequest, params: str = "v31") -> EstimateResult:
    ref = {
        **reference_for(DATA, "india"),
        "parameters": DATA.parameter_set(params),
        "clarity": CFG.requirement_clarity,
    }
    plan = plan_quick(CFG, req, None, "test")
    return calculate(plan_to_input(plan, req.name, ref, date(2026, 11, 2), 7, 100))


def build_cost(result: EstimateResult) -> Decimal:
    return sum(
        (Decimal(ln.likely_paise) for ln in result.lines if ln.stage in ("pre_build", "build")),
        Decimal(0),
    )


def test_front_end_only_builds_less_and_says_why() -> None:
    full, front = price(request("whole")), price(request("frontend_only"))
    assert build_cost(front) < build_cost(full) * Decimal("0.75")
    blocks = [ln for ln in front.lines if ln.bucket == "build.module_development"]
    assert blocks and all(ln.formula_id == "component_labour.v8" for ln in blocks)
    assert all(ln.formula_id != "component_labour.v8" for ln in full.lines)


def test_older_parameter_sets_ignore_the_answer() -> None:
    def features(result: EstimateResult) -> dict[str, int]:
        return {
            ln.line_key: ln.likely_paise
            for ln in result.lines
            if ln.bucket == "build.module_development"
        }

    full, front = price(request("whole"), "v30"), price(request("frontend_only"), "v30")
    assert all(ln.formula_id != "component_labour.v8" for ln in front.lines)
    same = features(full).keys() & features(front).keys()
    assert same and all(features(full)[k] == features(front)[k] for k in same)


def test_hidden_questions_take_the_answer_front_end_only_sets() -> None:
    req = request("frontend_only", hosting="aws", old_data="lot", scale="up_to_10l")
    assert _choice(CFG, req, "hosting").value == "existing"  # an earlier answer is dropped
    assert _choice(CFG, req, "old_data").value == "no"
    assert _choice(CFG, req, "web_domain").value == "client"
    whole = request("whole", hosting="aws", scale="up_to_10l")
    assert _choice(CFG, whole, "hosting").value == "aws"
    assert "performance_load_testing" in standard_blocks(CFG, whole)
    assert "performance_load_testing" not in standard_blocks(CFG, req)
    assert "audit_trail_logging" not in standard_blocks(CFG, req)


def test_a_description_that_keeps_the_backend_answers_the_question() -> None:
    found = suggest_features(
        CFG, "We want to redesign the app with new screens. Keep the existing backend and APIs."
    )
    assert found.reader == "basic"  # tests never call a real AI
    assert found.choices.get("build_part") == "frontend_only"
    assert "build_part" not in suggest_features(CFG, "A portal for citizens to apply").choices

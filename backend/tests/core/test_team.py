"""The team follows the work (parameter sets v34+, formula staffing.v1, OPEN_QUESTIONS 229): a
role with no work is not on the team, a role with too little work hands it to someone already
there (slowed down), a booking's worth of work or an answer that needs the role brings it in,
the project manager joins only with enough management work or formal reports, and no work is
ever dropped."""

from datetime import date
from decimal import Decimal
from typing import Any, Literal

import pytest

from app.core.config import get_settings
from app.services.calibration.backtest import reference_for
from app.services.engine.core import calculate
from app.services.engine.formulas import FORMULAS
from app.services.engine.outputs import EstimateResult
from app.services.engine.reference import Staffing, StaffRole
from app.services.engine.staffing import decide
from app.services.quick.config import quick_config
from app.services.quick.service import QuickRequest, plan_quick, plan_to_input
from app.services.seeding.reference import load_reference

Level = Literal["basic", "standard", "advanced"]
CFG = quick_config()
DATA = load_reference(get_settings().seeds_dir)
D = Decimal
RATES = {
    "role.qa_engineer": D(2000),
    "role.developer": D(3000),
    "role.senior_developer": D(7000),
    "role.solution_architect": D(12000),
}


def staffing(**roles: StaffRole) -> Staffing:
    return Staffing(source="test", roles={f"role.{k}": v for k, v in roles.items()})


QA = StaffRole(fallback="role.developer", slowdown=D("1.2"), min_booking_pd=D(5))
SENIOR = StaffRole(fallback="role.developer", slowdown=D("1.3"), min_booking_pd=D(5))


def team_for(work: dict[str, int], s: Staffing, **answers: Any) -> Any:
    return decide(s, {f"role.{k}": D(v) for k, v in work.items()}, RATES.__getitem__, answers.get)


def test_a_booking_worth_of_work_brings_the_role_in() -> None:
    team = team_for({"qa_engineer": 6}, staffing(qa_engineer=QA))
    assert team.done_by("role.qa_engineer") == ("role.qa_engineer", 1)


def test_too_little_work_goes_to_the_developer_slowed_down() -> None:
    team = team_for({"qa_engineer": 1}, staffing(qa_engineer=QA))
    assert team.done_by("role.qa_engineer") == ("role.developer", D("1.2"))
    assert "under a 5 day booking" in team.decisions["role.qa_engineer"].reason


def test_a_cheap_specialist_joins_when_booking_costs_no_more() -> None:
    # 4 pd: booking 5 × 2000 = 10,000 against the developer 4 × 1.2 × 3000 = 14,400
    team = team_for({"qa_engineer": 4}, staffing(qa_engineer=QA))
    assert team.decisions["role.qa_engineer"].joins


def test_an_answer_can_require_the_role() -> None:
    needed = QA.model_copy(update={"required_when": {"security_level": ["very_high"]}})
    s = staffing(qa_engineer=needed)
    assert (
        team_for({"qa_engineer": 1}, s, security_level="very_high")
        .decisions["role.qa_engineer"]
        .joins
    )
    assert (
        not team_for({"qa_engineer": 1}, s, security_level="standard")
        .decisions["role.qa_engineer"]
        .joins
    )


def test_work_moves_down_a_chain() -> None:
    architect = StaffRole(fallback="role.senior_developer", slowdown=D("1.2"), min_booking_pd=D(3))
    s = staffing(solution_architect=architect, senior_developer=SENIOR)
    team = team_for({"solution_architect": 1, "senior_developer": 2}, s)
    # the senior gets 2 + 1 × 1.2 = 3.2 pd, under its booking: the developer does both
    assert team.done_by("role.solution_architect") == ("role.developer", D("1.56"))
    assert team.decisions["role.senior_developer"].work_pd == D("3.2")


def test_a_role_with_no_work_is_not_on_the_team() -> None:
    team = team_for({"senior_developer": 9}, staffing(qa_engineer=QA, senior_developer=SENIOR))
    assert "role.qa_engineer" not in team.decisions


def test_a_fallback_decided_first_is_refused() -> None:
    with pytest.raises(ValueError, match="decided before it"):
        staffing(senior_developer=SENIOR, solution_architect=SENIOR.model_copy(
            update={"fallback": "role.senior_developer"}))  # fmt: skip


def price(version: str, features: list[str], level: Level, **choices: Any) -> EstimateResult:
    req = QuickRequest(
        name="team", features=features, feature_levels=dict.fromkeys(features, level),
        choices={"support_years": 1, **choices},
    )  # fmt: skip
    ref = {
        **reference_for(DATA, "india"),
        "parameters": DATA.parameter_set(version),
        "clarity": CFG.requirement_clarity,
    }
    plan = plan_quick(CFG, req, None, "test")
    return calculate(plan_to_input(plan, req.name, ref, date(2026, 11, 10), 7, 100))


def roles(result: EstimateResult, *stages: str) -> dict[str, Decimal]:
    out: dict[str, Decimal] = {}
    for m in result.manpower:
        if m.stage in stages:
            out[m.role] = out.get(m.role, D(0)) + m.person_days
    return out


TINY: tuple[list[str], Level] = (["online_forms"], "basic")
LARGE: tuple[list[str], Level] = (
    ["online_forms", "payments", "dashboards", "documents", "ai_chatbot", "bookings"],
    "advanced",
)


def test_a_tiny_site_has_a_small_team_and_no_project_manager() -> None:
    before, after = (
        roles(price("v33", *TINY), "build", "pre_build", "programme"),
        roles(price("v34", *TINY), "build", "pre_build", "programme"),
    )
    gone = {"role.project_manager", "role.security_engineer", "role.solution_architect"}
    assert gone <= set(before) and not gone & set(after)
    assert len(after) < len(before)
    # the work is not dropped: it is done by someone else, a little slower
    assert sum(after.values()) > sum(before.values())


def test_a_large_project_keeps_its_specialists() -> None:
    team = roles(price("v34", *LARGE), "build", "pre_build", "programme")
    assert {"role.project_manager", "role.qa_engineer", "role.solution_architect"} <= set(team)


def test_formal_reports_need_a_project_manager() -> None:
    team = roles(price("v34", *TINY, reporting="yes"), "programme")
    assert "role.project_manager" in team


def test_the_trace_says_why() -> None:
    result = price("v34", *TINY)
    line = next(ln for ln in result.lines if ln.bucket == "build.module_development")
    reasons = line.inputs.get("staffing")
    assert isinstance(reasons, dict) and reasons["formula"] == "staffing.v1"
    assert "staffing.v1" in FORMULAS
    pm = next(ln for ln in result.lines if ln.line_key == "programme.project_management/pm")
    assert pm.trace is not None and any("managed by the" in s.label for s in pm.trace.steps)


def test_older_sets_keep_every_role() -> None:
    assert "role.project_manager" in roles(price("v33", *TINY), "programme")

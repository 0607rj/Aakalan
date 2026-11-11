"""Who builds it (parameter sets v32+, OPEN_QUESTIONS 195): every person's day rate × the
builder's factor; a mid-size firm is the calibrated level, and bought items do not change."""

from datetime import date
from decimal import Decimal

from app.core.config import get_settings
from app.services.calibration.backtest import reference_for
from app.services.engine.core import calculate
from app.services.engine.outputs import EstimateResult
from app.services.quick.config import quick_config
from app.services.quick.service import QuickRequest, plan_quick, plan_to_input
from app.services.seeding.reference import load_reference

CFG = quick_config()
DATA = load_reference(get_settings().seeds_dir)


def price(builder: str | None, params: str = "v32", build_type: str = "custom") -> EstimateResult:
    # the build approach is pinned: its default follows the builder (OPEN_QUESTIONS 238)
    choices: dict[str, str | int] = {"build_type": build_type}
    if builder:
        choices["builder"] = builder
    req = QuickRequest(
        name="clinic", mode="client", features=["public_website", "bookings"], choices=choices
    )
    ref = {
        **reference_for(DATA, "india"),
        "parameters": DATA.parameter_set(params),
        "clarity": CFG.requirement_clarity,
    }
    plan = plan_quick(CFG, req, None, "test")
    return calculate(plan_to_input(plan, req.name, ref, date(2026, 11, 2), 7, 100))


def line(result: EstimateResult, bucket: str) -> Decimal:
    return sum((Decimal(ln.likely_paise) for ln in result.lines if ln.bucket == bucket), Decimal(0))


def test_people_cost_follows_the_builder() -> None:
    free, mid, large = price("freelancer"), price("mid_firm"), price("large_firm")
    work = "build.module_development"
    lines = sum(1 for ln in mid.lines if ln.bucket == work)  # each line rounds to a paisa
    assert abs(line(free, work) - line(mid, work) * Decimal("0.5")) <= lines
    assert abs(line(large, work) - line(mid, work) * 2) <= lines
    assert free.totals and mid.totals and large.totals
    assert free.totals.p50_paise < mid.totals.p50_paise < large.totals.p50_paise
    step = next(
        s
        for ln in free.lines
        if ln.bucket == work
        for s in ln.trace.steps
        if "freelancer" in s.label
    )
    assert "× 0.5" in step.expression


def test_bought_items_do_not_change() -> None:
    free, large = price("freelancer"), price("large_firm")
    assert line(free, "run.hosting") == line(large, "run.hosting")
    assert line(free, "build.tools") == line(large, "build.tools")


def test_mid_size_is_the_default_and_v31_ignores_the_answer() -> None:
    assert price(None).totals == price("mid_firm").totals
    old = price(None, "v31").totals
    assert old is not None and price("freelancer", "v31").totals == old


def test_small_builders_default_to_ready_parts() -> None:
    """OPEN_QUESTIONS 238: left unanswered, a freelancer or small company builds on a
    framework's ready parts; a mid-size company keeps "made fully to order"; an answer wins."""

    def build_type(choices: dict[str, str | int]) -> str:
        req = QuickRequest(name="clinic", features=["bookings"], choices=choices)
        plan = plan_quick(CFG, req, None, "test")
        return str(plan.answers["build_type"][0])

    assert build_type({"builder": "small_firm"}) == "framework"
    assert build_type({"builder": "freelancer"}) == "framework"
    assert build_type({"builder": "mid_firm"}) == "custom"
    assert build_type({"builder": "small_firm", "build_type": "custom"}) == "custom"


def team(builder: str) -> dict[str, Decimal]:
    req = QuickRequest(
        name="clinic",
        features=["online_forms", "staff_login", "dashboards", "bookings", "notifications"],
        choices={"builder": builder, "build_type": "custom"},
    )
    ref = {
        **reference_for(DATA, "india"),
        "parameters": DATA.parameter_set("v39"),
        "clarity": CFG.requirement_clarity,
    }
    plan = plan_quick(CFG, req, None, "test")
    result = calculate(plan_to_input(plan, req.name, ref, date(2026, 11, 11), 7, 100))
    roles: dict[str, Decimal] = {}
    for m in result.manpower:
        roles[m.role] = roles.get(m.role, Decimal(0)) + m.person_days
    return roles


def test_the_team_follows_who_builds_it() -> None:
    """OPEN_QUESTIONS 238 (v39): a freelancer does the specialists' work itself, a small
    company books a specialist only with a month of work (never a writer or trainer), a large
    company books a separate person for every kind of work; the work is never dropped."""
    free, small, mid, large = (
        team(b) for b in ("freelancer", "small_firm", "mid_firm", "large_firm")
    )
    assert set(free) == {"role.developer", "role.senior_developer"}
    assert not {"role.technical_writer", "role.trainer", "role.solution_architect"} & set(small)
    assert all(
        pd >= 22
        for r, pd in small.items()
        if r not in {"role.developer", "role.senior_developer", "role.qa_engineer"}
    )
    assert set(large) == set(mid) and "role.project_manager" in large
    assert len(free) < len(small) < len(mid)
    # handed-over work is slowed, never lost
    assert sum(free.values()) > sum(mid.values())


def test_builder_teams_name_known_roles() -> None:
    import pytest

    from app.services.engine.reference import Staffing

    rules = DATA.parameter_set("v39").staffing
    assert rules is not None
    bad = rules.model_dump(mode="json")
    bad["by_builder"]["freelancer"]["not_booked"].append("role.astronaut")
    with pytest.raises(ValueError, match="astronaut"):
        Staffing.model_validate(bad)

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


def price(builder: str | None, params: str = "v32") -> EstimateResult:
    choices: dict[str, str | int] = {"builder": builder} if builder else {}
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

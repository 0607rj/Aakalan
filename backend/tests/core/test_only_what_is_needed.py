"""Only what the project needs is priced (OPEN_QUESTIONS 196): the web firewall above 10,000
users, the SMS connection and fees only when SMS is sent, the requirement study on small and
small-to-medium projects only with milestone payments (a tender), and the builder's financing
cost from how it is paid."""

from datetime import date
from decimal import Decimal
from typing import Any

from app.core.config import get_settings
from app.services.calibration.backtest import reference_for
from app.services.engine.core import calculate
from app.services.engine.outputs import EstimateResult
from app.services.quick.config import quick_config
from app.services.quick.service import QuickRequest, plan_quick, plan_to_input
from app.services.seeding.reference import load_reference

CFG = quick_config()
DATA = load_reference(get_settings().seeds_dir)
FEATURES = ["public_website", "bookings", "payments", "notifications"]


def price(scope: list[str] | None = None, **choices: Any) -> EstimateResult:
    req = QuickRequest(
        name="clinic", mode="client", features=FEATURES, scope=scope or [], choices=choices
    )
    ref = {
        **reference_for(DATA, "india"),
        "parameters": DATA.parameter_set("v32"),
        "clarity": CFG.requirement_clarity,
    }
    plan = plan_quick(CFG, req, None, "test")
    return calculate(plan_to_input(plan, req.name, ref, date(2026, 11, 2), 7, 100))


def labels(result: EstimateResult) -> set[str]:
    return {ln.label for ln in result.lines if ln.likely_paise > 0}


def amount(result: EstimateResult, bucket: str) -> Decimal:
    return sum((Decimal(ln.likely_paise) for ln in result.lines if ln.bucket == bucket), Decimal(0))


def has(result: EstimateResult, words: str) -> bool:
    return any(words in label for label in labels(result))


def test_a_small_private_site_has_no_extras() -> None:
    result = price()
    assert not has(result, "Web firewall")
    assert not has(result, "SMS / email gateway") and not has(result, "Messages by SMS")
    assert not has(result, "Discovery and requirement study")


def test_each_extra_comes_back_when_the_project_needs_it() -> None:
    assert has(price(scale="up_to_25k"), "Web firewall")
    with_sms = price(scope=["sms"])
    assert has(with_sms, "Messages by SMS")  # the connection; the message fees the client pays
    assert has(price(payment_terms="milestones"), "Discovery and requirement study")


def test_paying_in_advance_costs_the_builder_almost_nothing_to_fund() -> None:
    advance = amount(price(), "commercial.working_capital")
    tender = amount(price(payment_terms="milestones"), "commercial.working_capital")
    assert advance * 10 < tender
    line = next(ln for ln in price().lines if ln.bucket == "commercial.working_capital")
    assert line.formula_id == "commercial.working_capital.v3"

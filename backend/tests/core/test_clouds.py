"""OPEN_QUESTIONS 240 (rate card v13, parameters v39): Microsoft Azure and Google Cloud are
priced from their own Indian-region price points; Amazon stays the default public cloud."""

from datetime import date
from decimal import Decimal

from app.core.config import get_settings
from app.services.calibration.backtest import reference_for
from app.services.engine.core import calculate
from app.services.quick.config import quick_config
from app.services.quick.service import QuickRequest, plan_quick, plan_to_input
from app.services.seeding.reference import load_reference

CFG = quick_config()
DATA = load_reference(get_settings().seeds_dir)


def hosting(choices: dict[str, str | int]) -> tuple[str, Decimal, list[str]]:
    req = QuickRequest(name="clinic", features=["bookings"], choices=choices)
    ref = {**reference_for(DATA, "india"), "clarity": CFG.requirement_clarity}
    plan = plan_quick(CFG, req, None, "test")
    result = calculate(plan_to_input(plan, req.name, ref, date(2026, 11, 11), 7, 100))
    lines = [ln for ln in result.lines if ln.bucket == "run.hosting"]
    keys = [r.key for ln in lines for r in ln.trace.rate_items]
    return (
        str(plan.answers["hosting_provider"][0]),
        sum((Decimal(ln.likely_paise) for ln in lines), Decimal(0)),
        keys,
    )


def test_each_public_cloud_is_priced_from_its_own_prices() -> None:
    aws, azure, gcp = (
        hosting({"hosting": "aws", "cloud_provider": c}) for c in ("aws", "azure", "gcp")
    )
    assert (aws[0], azure[0], gcp[0]) == ("aws", "azure", "gcp")
    assert all(k.startswith("hosting.azure.") for k in azure[2] if k.startswith("hosting."))
    assert all(k.startswith("hosting.gcp.") for k in gcp[2] if k.startswith("hosting."))
    assert len({aws[1], azure[1], gcp[1]}) == 3
    assert hosting({"hosting": "aws"})[0] == "aws"  # skipped: Amazon


def test_the_cloud_question_never_undoes_another_hosting_choice() -> None:
    assert hosting({"hosting": "indian_cloud", "cloud_provider": "gcp"})[0] == "indian_cloud"

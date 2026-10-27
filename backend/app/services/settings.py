"""Company settings: how *this* company prices (margin, safety buffer, how lean or thorough its
build and support effort is). Applied on top of the published parameter set when an estimate is
built, and recorded in the estimate snapshot, so every estimate stays reproducible."""

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import OrgSettings
from app.services.engine.reference import Calibration, ParameterSet, RateCard, RateKind

ONE = Decimal(1)
COMPANY = "company"  # suffix on a rate card version that carries this company's own rates


class CompanySettings(BaseModel):
    margin_percent: Decimal | None = Field(default=None, ge=0, le=1)  # None = parameter default
    contingency_percent: Decimal | None = Field(default=None, ge=0, le=1)  # None = from clarity
    build_effort_multiplier: Decimal = Field(default=ONE, ge=Decimal("0.3"), le=Decimal(3))
    support_effort_multiplier: Decimal = Field(default=ONE, ge=Decimal("0.3"), le=Decimal(3))
    # The company's own cost per person-day by role (rupees), replacing public market averages.
    role_day_rates: dict[str, Decimal] = {}
    # How much the company's team uses AI tools (None = the parameter set's default).
    team_ai_maturity: Literal["none", "low", "medium", "high"] | None = None
    # How much of the AI saving the price passes to the client (the quick estimate's
    # ai_passthrough answer; None = the question's default, all). OPEN_QUESTIONS 173.
    ai_passthrough: Literal["all", "most", "half", "keep"] | None = None


def company_settings(db: Session, org_id: str) -> CompanySettings:
    row = db.scalars(select(OrgSettings).where(OrgSettings.org_id == org_id)).first()
    return CompanySettings.model_validate(row.data) if row else CompanySettings()


def save_company_settings(db: Session, org_id: str, settings: CompanySettings) -> CompanySettings:
    row = db.scalars(select(OrgSettings).where(OrgSettings.org_id == org_id)).first()
    data = settings.model_dump(mode="json")
    if row is None:
        db.add(OrgSettings(org_id=org_id, data=data))
    else:
        row.data = data
    db.commit()
    return settings


def apply_company_settings(params: ParameterSet, settings: CompanySettings) -> ParameterSet:
    """Parameter set as this company uses it: margin/buffer defaults replaced, calibration dials
    multiplied by the company's effort adjustments."""
    defaults = dict(params.defaults.values)
    if settings.margin_percent is not None:
        defaults["margin_percent"] = str(settings.margin_percent)
    if settings.contingency_percent is not None:
        defaults["contingency_percent"] = str(settings.contingency_percent)
    if settings.team_ai_maturity is not None:
        defaults["team_ai_maturity"] = settings.team_ai_maturity
    base = params.calibration or Calibration(source="none")
    changed = settings.build_effort_multiplier != ONE or settings.support_effort_multiplier != ONE
    calibration = base.model_copy(
        update={
            "effort_multiplier": base.effort_multiplier * settings.build_effort_multiplier,
            "run_multiplier": base.run_multiplier * settings.support_effort_multiplier,
            "source": f"{base.source} + company settings" if changed else base.source,
        }
    )
    return params.model_copy(
        update={
            "defaults": params.defaults.model_copy(update={"values": defaults}),
            "calibration": calibration if (params.calibration or changed) else None,
        }
    )


def apply_company_rates(card: RateCard, settings: CompanySettings) -> RateCard:
    """The rate card with this company's own day rates for the roles it has set (rupee cards
    only). The version gets a '+company' suffix so the estimate shows its rates are the
    company's, and each replaced rate says so in its source."""
    rates = {k: v for k, v in settings.role_day_rates.items() if v > 0}
    if not rates or card.currency != "INR":
        return card
    items = [
        item.model_copy(
            update={
                "amount": rates[item.key],
                "source": f"Company settings (market rate was {item.amount})",
                "source_url": None,
            }
        )
        if item.kind == RateKind.ROLE and item.key in rates
        else item
        for item in card.items
    ]
    return card.model_copy(update={"items": items, "version": f"{card.version}+{COMPANY}"})


def market_role_rates(card: RateCard) -> dict[str, Decimal]:
    """Public market day rates by role from the published card (for the Settings page)."""
    return {i.key: i.amount for i in card.items if i.kind == RateKind.ROLE}

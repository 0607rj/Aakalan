"""Company pricing settings."""

from datetime import UTC, datetime

from fastapi import APIRouter
from pydantic import BaseModel

from app.api.deps import CurrentUser, DbSession, FinanceUser
from app.services.estimates.reference_store import get_rate_card
from app.services.quick.config import quick_config
from app.services.settings import (
    CompanySettings,
    company_settings,
    market_role_rates,
    save_company_settings,
)

router = APIRouter(tags=["settings"])


@router.get("/settings", response_model=CompanySettings)
def read_settings(db: DbSession, user: CurrentUser) -> CompanySettings:
    return company_settings(db, user.org_id)


@router.put("/settings", response_model=CompanySettings)
def update_settings(body: CompanySettings, db: DbSession, user: FinanceUser) -> CompanySettings:
    """Margin and effort settings apply to every new estimate; finance or admin only."""
    return save_company_settings(db, user.org_id, body)


class RoleRate(BaseModel):
    key: str  # rate card key, e.g. "role.developer"
    label: str
    market_rupees_per_day: str  # public market average (Decimal string)
    hours_per_day: int  # to enter or show the rate per hour


@router.get("/settings/roles", response_model=list[RoleRate])
def roles(db: DbSession, _user: CurrentUser) -> list[RoleRate]:
    """Roles the estimator prices, with today's public market day rate for comparison."""
    card = get_rate_card(db, None, datetime.now(UTC).date())
    return [
        RoleRate(
            key=key,
            label=key.removeprefix("role.").replace("_", " ").capitalize(),
            market_rupees_per_day=str(amount),
            hours_per_day=quick_config().hours_per_person_day,
        )
        for key, amount in market_role_rates(card).items()
    ]

"""Admin: versioned rate cards, parameter sets and catalog. Versions are immutable; publishing
new values means posting a new version (rule 4)."""

from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select

from app.api.deps import AdminUser, DbSession, EditorUser
from app.models import ParameterSet, RateCard
from app.services.engine import reference as ref
from app.services.estimates.reference_store import get_catalog
from app.services.seeding.database import add_rate_card, rate_card_model

router = APIRouter(prefix="/admin", tags=["admin"])


class RateCardSummary(BaseModel):
    version: str
    effective_date: str
    status: str
    source: str
    item_count: int
    placeholder_count: int


class ParameterSetSummary(BaseModel):
    version: str
    effective_date: str
    status: str


@router.get("/rate-cards", response_model=list[RateCardSummary])
def list_rate_cards(db: DbSession, _user: EditorUser) -> list[RateCardSummary]:
    rows = db.scalars(select(RateCard).order_by(RateCard.effective_date.desc()))
    return [
        RateCardSummary(
            version=r.version,
            effective_date=r.effective_date.isoformat(),
            status=r.status,
            source=r.source,
            item_count=len(r.items),
            placeholder_count=sum(1 for i in r.items if i.source == ref.PLACEHOLDER),
        )
        for r in rows
    ]


@router.get("/rate-cards/{version}", response_model=ref.RateCard)
def get_rate_card(version: str, db: DbSession, _user: EditorUser) -> ref.RateCard:
    row = db.scalars(select(RateCard).where(RateCard.version == version)).first()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Rate card not found")
    return rate_card_model(row)


@router.post("/rate-cards", response_model=ref.RateCard, status_code=status.HTTP_201_CREATED)
def create_rate_card(body: ref.RateCard, db: DbSession, _user: AdminUser) -> ref.RateCard:
    if db.scalars(select(RateCard).where(RateCard.version == body.version)).first():
        raise HTTPException(status.HTTP_409_CONFLICT, "Version exists; versions are immutable")
    row = add_rate_card(db, body)
    db.commit()
    return rate_card_model(row)


@router.get("/parameter-sets", response_model=list[ParameterSetSummary])
def list_parameter_sets(db: DbSession, _user: EditorUser) -> list[ParameterSetSummary]:
    rows = db.scalars(select(ParameterSet).order_by(ParameterSet.effective_date.desc()))
    return [
        ParameterSetSummary(
            version=r.version, effective_date=r.effective_date.isoformat(), status=r.status
        )
        for r in rows
    ]


@router.get("/parameter-sets/{version}")
def get_parameter_set(version: str, db: DbSession, _user: EditorUser) -> dict[str, Any]:
    row = db.scalars(select(ParameterSet).where(ParameterSet.version == version)).first()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Parameter set not found")
    return row.data


@router.get("/catalog", response_model=ref.Catalog)
def get_full_catalog(db: DbSession, _user: EditorUser) -> ref.Catalog:
    return get_catalog(db)

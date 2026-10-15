"""Read versioned reference data from the database as engine models."""

from datetime import date

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import CatalogComponent, ParameterSet, RateCard, TaxonomyVersion
from app.services.engine import reference as ref
from app.services.seeding.database import rate_card_model


def _missing(what: str) -> HTTPException:
    return HTTPException(status.HTTP_409_CONFLICT, f"No {what} found; run `make seed`.")


def get_rate_card(db: Session, version: str | None, as_of: date) -> ref.RateCard:
    """The requested version, else the active card with the latest effective date <= as_of."""
    query = select(RateCard)
    if version is not None:
        query = query.where(RateCard.version == version)
    else:
        query = query.where(RateCard.status == "active", RateCard.effective_date <= as_of).order_by(
            RateCard.effective_date.desc(), RateCard.created_at.desc()
        )
    row = db.scalars(query).first()
    if row is None:
        raise _missing(f"rate card {version or '(active)'}")
    return rate_card_model(row)


def get_parameter_set(db: Session, version: str | None, as_of: date) -> ref.ParameterSet:
    query = select(ParameterSet)
    if version is not None:
        query = query.where(ParameterSet.version == version)
    else:
        query = query.where(
            ParameterSet.status == "active", ParameterSet.effective_date <= as_of
        ).order_by(ParameterSet.effective_date.desc(), ParameterSet.created_at.desc())
    row = db.scalars(query).first()
    if row is None:
        raise _missing(f"parameter set {version or '(active)'}")
    return ref.ParameterSet.model_validate(row.data)


def latest_catalog_version(db: Session) -> str:
    row = db.scalars(
        select(CatalogComponent.version).order_by(CatalogComponent.created_at.desc())
    ).first()
    if row is None:
        raise _missing("component catalog")
    return row


def get_catalog(db: Session, version: str | None = None) -> ref.Catalog:
    version = version or latest_catalog_version(db)
    rows = db.scalars(
        select(CatalogComponent)
        .where(CatalogComponent.version == version)
        .order_by(CatalogComponent.created_at, CatalogComponent.key)
    ).all()
    if not rows:
        raise _missing(f"catalog {version}")
    return ref.Catalog(
        version=version,
        components=[ref.CatalogComponent.model_validate(r.spec) for r in rows],
    )


def get_taxonomy(db: Session, version: str | None = None) -> ref.Taxonomy:
    query = select(TaxonomyVersion)
    if version is not None:
        query = query.where(TaxonomyVersion.version == version)
    row = db.scalars(query.order_by(TaxonomyVersion.created_at.desc())).first()
    if row is None:
        raise _missing("taxonomy")
    return ref.Taxonomy.model_validate(row.data)

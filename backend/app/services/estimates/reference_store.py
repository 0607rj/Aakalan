"""Read versioned reference data from the database as engine models."""

from collections.abc import Sequence
from datetime import date
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.tenancy import scoped
from app.models import (
    CatalogComponent,
    ParameterSet,
    RateCard,
    ResearchedComponent,
    TaxonomyVersion,
)
from app.services.engine import reference as ref
from app.services.research.library import shared_blocks
from app.services.seeding.database import rate_card_model

DEFAULT_REGION = "india"
REGIONS = ("india", "us")


def _missing(what: str) -> HTTPException:
    return HTTPException(status.HTTP_409_CONFLICT, f"No {what} found; run `make seed`.")


def get_rate_card(
    db: Session, version: str | None, as_of: date, region: str = DEFAULT_REGION
) -> ref.RateCard:
    """The requested version, else the country's active card with the latest effective date
    <= as_of (same date: the most recently added, then the highest version)."""
    query = select(RateCard)
    if version is not None:  # a "+company" card is the published card with company rates
        query = query.where(RateCard.version == version.split("+", 1)[0])
    else:
        query = query.where(
            RateCard.status == "active",
            RateCard.effective_date <= as_of,
            RateCard.region == region,
        )
    row = _newest(db.scalars(query).all())
    if row is None:
        raise _missing(f"rate card {version or '(active)'}")
    return rate_card_model(row)


def get_parameter_set(
    db: Session, version: str | None, as_of: date, region: str = DEFAULT_REGION
) -> ref.ParameterSet:
    query = select(ParameterSet)
    if version is not None:
        query = query.where(ParameterSet.version == version)
    else:
        query = query.where(
            ParameterSet.status == "active",
            ParameterSet.effective_date <= as_of,
            ParameterSet.region == region,
        )
    row = _newest(db.scalars(query).all())
    if row is None:
        raise _missing(f"parameter set {version or '(active)'}")
    return ref.ParameterSet.model_validate(row.data)


def latest_catalog_version(db: Session) -> str:
    versions = set(db.scalars(select(CatalogComponent.version)))
    if not versions:
        raise _missing("component catalog")
    return max(versions, key=_version_number)


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


def catalog_for(
    db: Session, org_id: str, version: str | None = None, shared: bool = True
) -> ref.Catalog:
    """The published catalog plus researched blocks (services/research): the organisation's
    active ones, then the shared library's (only while sharing is on), less any the
    organisation retired. `shared=False` for anything listed to a user: other companies'
    blocks price and match features quietly, never shown by name (OPEN_QUESTIONS 185). The
    estimate's snapshot stores the merged list, so an estimate never changes when blocks are
    researched, shared or retired later."""
    catalog = get_catalog(db, version)
    rows = db.scalars(
        scoped(ResearchedComponent, org_id).order_by(
            ResearchedComponent.created_at, ResearchedComponent.key
        )
    ).all()
    others = shared_blocks(db) if shared else []
    keys = {c.key for c in catalog.components} | {r.key for r in rows if r.status == "retired"}
    extra: list[ref.CatalogComponent] = []
    for key, spec in [
        *((r.key, r.spec) for r in rows if r.status == "active"),
        *((s.key, s.spec) for s in others),
    ]:
        if key not in keys and spec is not None:
            extra.append(ref.CatalogComponent.model_validate(spec))
            keys.add(key)
    if not extra:
        return catalog
    return catalog.model_copy(update={"components": [*catalog.components, *extra]})


def _newest(rows: Sequence[Any]) -> Any:
    """Latest effective date; on the same date the most recently added, then the highest
    version in natural order (v10 after v9)."""
    if not rows:
        return None
    return max(rows, key=lambda r: (r.effective_date, r.created_at, ref.version_key(r.version)))


def _version_number(version: str) -> int:
    digits = version.lstrip("v")
    return int(digits) if digits.isdigit() else 0


def get_taxonomy(db: Session, version: str | None = None) -> ref.Taxonomy:
    """The requested version, else the newest (highest version number)."""
    query = select(TaxonomyVersion)
    if version is not None:
        query = query.where(TaxonomyVersion.version == version)
    rows = db.scalars(query).all()
    if not rows:
        raise _missing("taxonomy")
    row = max(rows, key=lambda r: _version_number(r.version))
    return ref.Taxonomy.model_validate(row.data)

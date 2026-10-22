"""Researched building blocks of the organisation (services/research): list them, research one
feature on demand, and retire one so later estimates no longer use it (estimates that used it
keep their own snapshot)."""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.api.deps import AdminUser, CurrentUser, DbSession, EditorUser
from app.core.tenancy import get_owned
from app.models import ResearchedComponent
from app.services.quick.config import quick_config
from app.services.research.service import ai_available, research_rows, resolve_features

router = APIRouter(tags=["research"])


class ResearchedBlockOut(BaseModel):
    id: str
    key: str
    name: str
    section: str
    base_type: str
    status: str  # active / no_evidence / retired
    note: str
    base_effort_pd: dict[str, str] | None  # S / M / L person-days, when active
    source: str | None
    sources: list[dict[str, Any]]  # web sources with their check, and analysis parts
    model: str
    input_tokens: int
    output_tokens: int
    created_at: datetime


class ResearchIn(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    category: str  # a custom feature type: module / integration / report / ai / mobile


class ResearchOut(BaseModel):
    ai_available: bool
    catalog_key: str | None  # the block that prices it; None = the generic type block
    block: ResearchedBlockOut | None


def _out(row: ResearchedComponent) -> ResearchedBlockOut:
    spec = row.spec or {}
    effort = spec.get("base_effort_pd")
    return ResearchedBlockOut(
        id=row.id,
        key=row.key,
        name=row.name,
        section=row.section,
        base_type=row.base_type,
        status=row.status,
        note=row.note,
        base_effort_pd={k: str(v) for k, v in effort.items()} if effort else None,
        source=spec.get("source"),
        sources=row.sources,
        model=row.model,
        input_tokens=row.input_tokens,
        output_tokens=row.output_tokens,
        created_at=row.created_at,
    )


@router.get("/research-blocks", response_model=list[ResearchedBlockOut])
def list_blocks(db: DbSession, user: CurrentUser) -> list[ResearchedBlockOut]:
    return [_out(r) for r in research_rows(db, user.org_id)]


@router.post("/research-blocks", response_model=ResearchOut)
def research(body: ResearchIn, db: DbSession, user: EditorUser) -> ResearchOut:
    """Find the block for one feature now: the catalog, else research (with an AI key)."""
    cfg = quick_config()
    if body.category not in cfg.custom_feature_types:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Unknown feature type")
    [key] = resolve_features(db, user, cfg, [(body.name, body.category)])
    db.commit()
    row = next((r for r in research_rows(db, user.org_id) if r.key == key), None)
    return ResearchOut(
        ai_available=ai_available(), catalog_key=key, block=_out(row) if row else None
    )


@router.post("/research-blocks/{block_id}/retire", response_model=ResearchedBlockOut)
def retire(block_id: str, db: DbSession, user: AdminUser) -> ResearchedBlockOut:
    row = get_owned(db, ResearchedComponent, block_id, user.org_id)
    row.status = "retired"
    db.commit()
    return _out(row)

"""The site owner's console (OWNER_EMAILS): every company and user on the site, their
estimates, and the account actions an operator needs (disable, role, verify, delete, look at an
account read only). The one deliberate exception to per-organisation isolation (rule 8,
OPEN_QUESTIONS 172): every route here is owner-only and reads across organisations."""

import logging
from datetime import timedelta
from pathlib import Path

from fastapi import APIRouter, HTTPException, Response, status
from pydantic import BaseModel
from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import InstrumentedAttribute, Session

from app.api.auth import user_out
from app.api.deps import DbSession, OwnerUser, is_owner
from app.core.security import create_access_token
from app.models import (
    Document,
    Estimate,
    Organisation,
    Project,
    Role,
    SharedResearchedComponent,
    User,
)
from app.models.base import Base, utcnow
from app.schemas.auth import TokenResponse
from app.services.email import EmailNotConfiguredError, get_email_sender
from app.services.email_templates import (
    Email,
    account_deleted_email,
    account_off_email,
    account_on_email,
)
from app.services.quick.config import quick_config
from app.services.quick.service import QuickSummary, summarise
from app.services.research import library

log = logging.getLogger(__name__)
router = APIRouter(prefix="/owner", tags=["owner"])

RECENT_DAYS = 30  # "estimates in the last 30 days" on the overview


class Overview(BaseModel):
    companies: int
    users: int
    active_users: int
    unverified_users: int
    projects: int
    estimates: int
    estimates_recent: int
    recent_days: int


class OwnerUserRow(BaseModel):
    id: str
    email: str
    full_name: str
    role: Role
    is_active: bool
    email_verified: bool
    is_owner: bool
    created_at: str
    org_id: str
    org_name: str
    org_members: int
    projects: int
    estimates: int
    last_estimate_at: str | None


class UserChange(BaseModel):
    is_active: bool | None = None
    role: Role | None = None
    email_verified: bool | None = None


def _counts(db: Session, column: InstrumentedAttribute[str]) -> dict[str, int]:
    """How many rows each organisation has in the column's table."""
    rows = db.execute(select(column, func.count()).group_by(column))
    return {row[0]: row[1] for row in rows}


def _rows(db: Session) -> list[OwnerUserRow]:
    members = _counts(db, User.org_id)
    projects = _counts(db, Project.org_id)
    estimates = _counts(db, Estimate.org_id)
    last = {
        row[0]: row[1]
        for row in db.execute(
            select(Estimate.org_id, func.max(Estimate.created_at)).group_by(Estimate.org_id)
        )
    }
    users = db.scalars(select(User).order_by(User.created_at.desc()))
    return [
        OwnerUserRow(
            id=u.id,
            email=u.email,
            full_name=u.full_name,
            role=u.role,
            is_active=u.is_active,
            email_verified=u.email_verified_at is not None,
            is_owner=is_owner(u),
            created_at=u.created_at.isoformat(),
            org_id=u.org_id,
            org_name=u.organisation.name,
            org_members=members.get(u.org_id, 0),
            projects=projects.get(u.org_id, 0),
            estimates=estimates.get(u.org_id, 0),
            last_estimate_at=last[u.org_id].isoformat() if u.org_id in last else None,
        )
        for u in users
    ]


def _target(db: Session, owner: User, user_id: str) -> User:
    """Another person's account; the owner's own and other owners' accounts are not changed
    from here (that would lock the site out of its own console)."""
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    if user.id == owner.id or is_owner(user):
        raise HTTPException(status.HTTP_409_CONFLICT, "An owner account cannot be changed here")
    return user


@router.get("/overview", response_model=Overview)
def overview(db: DbSession, _owner: OwnerUser) -> Overview:
    def count(stmt: object) -> int:
        return int(db.scalar(stmt) or 0)  # type: ignore[call-overload]

    since = utcnow() - timedelta(days=RECENT_DAYS)
    return Overview(
        companies=count(select(func.count()).select_from(Organisation)),
        users=count(select(func.count()).select_from(User)),
        active_users=count(select(func.count()).select_from(User).where(User.is_active)),
        unverified_users=count(
            select(func.count()).select_from(User).where(User.email_verified_at.is_(None))
        ),
        projects=count(select(func.count()).select_from(Project)),
        estimates=count(select(func.count()).select_from(Estimate)),
        estimates_recent=count(
            select(func.count()).select_from(Estimate).where(Estimate.created_at >= since)
        ),
        recent_days=RECENT_DAYS,
    )


@router.get("/users", response_model=list[OwnerUserRow])
def list_users(db: DbSession, _owner: OwnerUser) -> list[OwnerUserRow]:
    """Every account on the site, newest first, with its company and how much it has used."""
    return _rows(db)


@router.get("/users/{user_id}/estimates", response_model=list[QuickSummary])
def user_estimates(user_id: str, db: DbSession, _owner: OwnerUser) -> list[QuickSummary]:
    """The latest estimate of every project in the user's company, newest first."""
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    latest: dict[str, Estimate] = {}
    for e in db.scalars(
        select(Estimate).where(Estimate.org_id == user.org_id).order_by(Estimate.created_at.desc())
    ):
        latest.setdefault(e.project_id, e)
    out = []
    for e in latest.values():
        project = db.get(Project, e.project_id)
        if project is not None:
            out.append(summarise(e, project, quick_config(), margin_visible=True))
    return out


@router.patch("/users/{user_id}", response_model=OwnerUserRow)
def change_user(user_id: str, body: UserChange, db: DbSession, owner: OwnerUser) -> OwnerUserRow:
    """Disable or enable an account (disabling signs it out everywhere), change its role, or
    mark its email as verified."""
    user = _target(db, owner, user_id)
    turned: bool | None = None
    if body.is_active is not None and body.is_active != user.is_active:
        user.is_active = turned = body.is_active
        if not body.is_active:
            user.token_version += 1
    if body.role is not None and body.role != user.role:
        user.role = body.role
        user.token_version += 1  # the role is in the token; sign in again to pick it up
    if body.email_verified is not None:
        user.email_verified_at = (
            (user.email_verified_at or utcnow()) if body.email_verified else None
        )
    db.commit()
    if turned is not None:
        _tell(user.email, account_on_email() if turned else account_off_email())
    return next(r for r in _rows(db) if r.id == user.id)


@router.post("/users/{user_id}/view", response_model=TokenResponse)
def view_as(user_id: str, db: DbSession, owner: OwnerUser) -> TokenResponse:
    """A short read-only session as this user, to see their estimates exactly as they do. The
    token names the owner (`act`); anything but reading is refused (api/deps.py)."""
    user = _target(db, owner, user_id)
    if not user.is_active:
        raise HTTPException(status.HTTP_409_CONFLICT, "Enable the account first to view it")
    token = create_access_token(
        user.id, user.org_id, user.role.value, user.token_version, acting_owner=owner.id
    )
    return TokenResponse(access_token=token, user=user_out(user))


# The person is told by email when the owner turns their account off or on, or deletes it: a
# deleted account cannot be told at sign-in, its address is gone (OPEN_QUESTIONS 222, 223).
def _tell(email: str, mail: Email) -> None:
    """Email the person; a failed email never undoes the owner's change (it is logged)."""
    try:
        get_email_sender().send(email, mail.subject, mail.text, mail.html)
    except EmailNotConfiguredError:
        log.warning("account email to %s not sent", email)


def _clear_references(db: Session, user_id: str) -> None:
    """Remove the user's name from records that stay (created by, confirmed by, ...)."""
    for table in Base.metadata.sorted_tables:
        for column in table.columns:
            if column.nullable and any(
                fk.column.table.name == User.__tablename__ for fk in column.foreign_keys
            ):
                db.execute(update(table).where(column == user_id).values({column.name: None}))


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: str, db: DbSession, owner: OwnerUser) -> Response:
    """Delete an account. When it is the only person in its company, the company goes too, with
    all its estimates, documents and uploaded files; otherwise the company and its work stay.
    Reference data and the shared research library are untouched."""
    user = _target(db, owner, user_id)
    org_id = user.org_id
    alone = db.scalar(select(func.count()).select_from(User).where(User.org_id == org_id)) == 1
    files = (
        [
            d.storage_path
            for d in db.scalars(select(Document).where(Document.org_id == org_id))
            if d.storage_path
        ]
        if alone
        else []
    )
    email = user.email
    _clear_references(db, user.id)
    db.execute(delete(User).where(User.id == user.id))
    if alone:
        db.execute(delete(Organisation).where(Organisation.id == org_id))
    db.commit()
    _tell(email, account_deleted_email(with_company=alone))
    for name in files:
        Path(name).unlink(missing_ok=True)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --- the shared research library: blocks wait for the owner before other companies use them --


class SharedBlockRow(BaseModel):
    id: str
    name: str  # the words it was researched under: one company's text
    section: str
    method: str  # web / analysis
    status: str  # pending / active / retired
    days: dict[str, str]  # person-days by size S / M / L (Decimal strings)
    sources: list[str]  # page addresses or catalog blocks the hours come from
    created_at: str


def _block_row(row: SharedResearchedComponent) -> SharedBlockRow:
    effort = row.spec.get("base_effort_pd") or {}
    sources = [
        str(s.get("url") or (f"{s['block']} ({s.get('level', '')})" if s.get("block") else ""))
        for s in row.sources
    ]
    return SharedBlockRow(
        id=row.id,
        name=row.name,
        section=row.section,
        method=row.method,
        status=row.status,
        days={str(k): str(v) for k, v in effort.items()},
        sources=[s for s in sources if s],
        created_at=row.created_at.isoformat(),
    )


@router.get("/shared-blocks", response_model=list[SharedBlockRow])
def shared_blocks(db: DbSession, _owner: OwnerUser) -> list[SharedBlockRow]:
    """The shared library, the blocks waiting for approval first."""
    rows = db.scalars(
        select(SharedResearchedComponent).order_by(SharedResearchedComponent.created_at.desc())
    ).all()
    order = {"pending": 0, "active": 1, "retired": 2}
    return [_block_row(r) for r in sorted(rows, key=lambda r: order.get(r.status, 3))]


def _shared(db: Session, block_id: str) -> SharedResearchedComponent:
    row = db.get(SharedResearchedComponent, block_id)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not found")
    return row


@router.post("/shared-blocks/{block_id}/approve", response_model=SharedBlockRow)
def approve_block(block_id: str, db: DbSession, _owner: OwnerUser) -> SharedBlockRow:
    """Let the block price other companies' features (under an anonymous key)."""
    row = _shared(db, block_id)
    library.approve(row)
    db.commit()
    return _block_row(row)


@router.post("/shared-blocks/{block_id}/retire", response_model=SharedBlockRow)
def retire_block(block_id: str, db: DbSession, _owner: OwnerUser) -> SharedBlockRow:
    """Stop offering the block to anyone; estimates that used it keep their own copy."""
    row = _shared(db, block_id)
    library.retire(row)
    db.commit()
    return _block_row(row)

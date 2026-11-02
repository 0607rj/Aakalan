"""Counted limits against abuse: sign-ups and contact messages per caller address, AI calls
per organisation and for the whole site, each in a rolling window. A limit of 0 is off.

`wait` says how many seconds until the next action is allowed (0 = now); `spend` records one
action or raises `LimitError` when the limit is reached. The numbers are settings
(core/config.py), not engine values."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import RateEvent
from app.models.base import utcnow

AI = "ai"
SIGNUP = "signup"
CONTACT = "contact"
SITE = "*"  # the key of the site-wide AI count


class LimitError(Exception):
    """Too many actions in the window; `seconds` until the next one is allowed."""

    def __init__(self, message: str, seconds: int) -> None:
        super().__init__(message)
        self.message = message
        self.seconds = seconds


def _aware(t: datetime) -> datetime:
    return t if t.tzinfo else t.replace(tzinfo=UTC)


def wait(db: Session, kind: str, key: str, limit: int, window: timedelta) -> int:
    """Seconds until one more `kind` action for `key` fits in the window (0 = now)."""
    if limit <= 0:
        return 0
    now = utcnow()
    db.execute(delete(RateEvent).where(RateEvent.kind == kind, RateEvent.created_at < now - window))
    times = db.scalars(
        select(RateEvent.created_at)
        .where(RateEvent.kind == kind, RateEvent.key == key, RateEvent.created_at >= now - window)
        .order_by(RateEvent.created_at.desc())
        .limit(limit)
    ).all()
    if len(times) < limit:
        return 0
    return int((_aware(times[-1]) + window - now).total_seconds()) + 1


def record(db: Session, kind: str, key: str) -> None:
    db.add(RateEvent(kind=kind, key=key))
    db.flush()


def _minutes(seconds: int) -> str:
    if seconds >= 3600:
        hours = -(-seconds // 3600)
        return f"{hours} hour{'s' * (hours > 1)}"
    minutes = max(1, -(-seconds // 60))
    return f"{minutes} minute{'s' * (minutes > 1)}"


def spend_signup(db: Session, ip: str) -> None:
    s = get_settings()
    seconds = wait(db, SIGNUP, ip, s.signup_ip_max_per_hour, timedelta(hours=1))
    if seconds:
        raise LimitError(f"Too many sign-ups from here. Try again in {_minutes(seconds)}.", seconds)
    record(db, SIGNUP, ip)


def spend_contact(db: Session, ip: str) -> None:
    s = get_settings()
    seconds = wait(db, CONTACT, ip, s.contact_ip_max_per_hour, timedelta(hours=1))
    if seconds:
        raise LimitError(f"Too many messages from here. Try again in {_minutes(seconds)}.", seconds)
    record(db, CONTACT, ip)


def ai_wait(db: Session, org_id: str) -> int:
    """Seconds until the organisation may make another AI call (0 = now)."""
    s = get_settings()
    day = timedelta(days=1)
    return max(
        wait(db, AI, org_id, s.ai_org_max_per_day, day),
        wait(db, AI, SITE, s.ai_site_max_per_day, day),
    )


def record_ai(db: Session, org_id: str) -> None:
    """Count one AI call for the organisation and the site (the caller checked `ai_wait`)."""
    record(db, AI, org_id)
    record(db, AI, SITE)


def spend_ai(db: Session, org_id: str) -> None:
    """Count one AI call for the organisation (and the site), or raise LimitError."""
    seconds = ai_wait(db, org_id)
    if seconds:
        raise LimitError(
            "Your company has used today's AI readings. Try again in "
            f"{_minutes(seconds)}, or fill in the form by hand.",
            seconds,
        )
    record_ai(db, org_id)

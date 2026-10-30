"""Organisations and users."""

import enum
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, IdTimestampMixin


class Role(enum.StrEnum):
    ADMIN = "admin"
    ESTIMATOR = "estimator"
    FINANCE = "finance"
    VIEWER = "viewer"


class Organisation(IdTimestampMixin, Base):
    __tablename__ = "organisations"

    name: Mapped[str] = mapped_column(String(200), unique=True)
    users: Mapped[list["User"]] = relationship(back_populates="organisation")


class User(IdTimestampMixin, Base):
    __tablename__ = "users"

    org_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organisations.id", ondelete="CASCADE"), index=True
    )
    email: Mapped[str] = mapped_column(String(320), unique=True)
    full_name: Mapped[str] = mapped_column(String(200), default="")
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[Role] = mapped_column(
        Enum(Role, native_enum=False, length=20, values_callable=lambda e: [m.value for m in e])
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    # Set once the address is proven by a one-time code (services/auth.py); sign-in needs it.
    email_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # In every access token; raised on a password reset or change, so older tokens stop working.
    token_version: Mapped[int] = mapped_column(Integer, default=0)

    organisation: Mapped[Organisation] = relationship(back_populates="users")


class OneTimeCode(IdTimestampMixin, Base):
    """A 6-digit code emailed to prove the address (verify_email) or reset a password
    (reset_password). Only a keyed hash is stored; a code works once, until `expires_at`, for
    a few attempts. Not a tenant table: it belongs to a user, never read by organisation."""

    __tablename__ = "one_time_codes"

    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    purpose: Mapped[str] = mapped_column(String(20))
    code_hash: Mapped[str] = mapped_column(String(64))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class LoginFailure(IdTimestampMixin, Base):
    """A wrong password at sign-in, by email (normalised, also for unknown addresses) and the
    caller's address, so guessing is slowed down (services/auth.py). Not a tenant table: it
    is read by email or address, never by organisation; rows older than the window go."""

    __tablename__ = "login_failures"

    email: Mapped[str] = mapped_column(String(320), index=True)
    ip: Mapped[str] = mapped_column(String(64), index=True)


class OrgSettings(IdTimestampMixin, Base):
    """Company pricing settings (margin, buffer, effort adjustments) — one row per org."""

    __tablename__ = "org_settings"

    org_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organisations.id", ondelete="CASCADE"), unique=True
    )
    data: Mapped[dict[str, Any]]

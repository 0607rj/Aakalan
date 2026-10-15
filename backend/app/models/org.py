"""Organisations and users."""

import enum

from sqlalchemy import Boolean, Enum, ForeignKey, String
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

    organisation: Mapped[Organisation] = relationship(back_populates="users")

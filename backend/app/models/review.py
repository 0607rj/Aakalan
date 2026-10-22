"""The AI's second opinion on an estimate (services/quick/second_opinion.py)."""

from typing import Any

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, IdTimestampMixin, TenantMixin


class SecondOpinion(IdTimestampMixin, TenantMixin, Base):
    """The latest AI review of one estimate: concerns about scope and levels in plain words,
    never a number. Asking again replaces it."""

    __tablename__ = "second_opinions"
    __table_args__ = (UniqueConstraint("org_id", "estimate_id"),)

    estimate_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("estimates.id", ondelete="CASCADE")
    )
    verdict: Mapped[str] = mapped_column(String(20))  # looks_right / check
    summary: Mapped[str] = mapped_column(String(600))
    flags: Mapped[list[Any]]  # [{kind, feature, message}]
    model: Mapped[str] = mapped_column(String(100))
    prompt_version: Mapped[str] = mapped_column(String(40))
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    created_by: Mapped[str | None] = mapped_column(String(36), nullable=True)

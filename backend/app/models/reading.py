"""The AI's reading of a description the user typed ("Find features"), kept per organisation."""

from typing import Any

from sqlalchemy import JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, IdTimestampMixin, TenantMixin


class DescriptionReading(IdTimestampMixin, TenantMixin, Base):
    """One reading of one description, so the same words give the same features every time
    (OPEN_QUESTIONS 181) without asking the AI again. Keyed by a fingerprint of the text, never
    the text itself; a new prompt version or model reads it again. Rows are never edited."""

    __tablename__ = "description_readings"
    __table_args__ = (UniqueConstraint("org_id", "text_sha256", "prompt_version", "model"),)

    text_sha256: Mapped[str] = mapped_column(String(64))
    prompt_version: Mapped[str] = mapped_column(String(40))
    model: Mapped[str] = mapped_column(String(100))  # the configured model
    output: Mapped[dict[str, Any]] = mapped_column(JSON)  # the reader's output (ExtractionOutput)

"""Building blocks researched from published web sources for features the catalog lacks."""

from typing import Any

from sqlalchemy import JSON, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, IdTimestampMixin, TenantMixin


class ResearchedComponent(IdTimestampMixin, TenantMixin, Base):
    """One researched feature. `active` rows carry a full catalog component (`spec`) that every
    later estimate of the organisation can use; `no_evidence` rows record a search that found
    no checkable source (so it is not repeated until it may be retried); `retired` rows are no
    longer offered (estimates that used them keep their own snapshot). Rows are never edited."""

    __tablename__ = "researched_components"
    __table_args__ = (UniqueConstraint("org_id", "key"),)

    key: Mapped[str] = mapped_column(String(100))  # catalog key, "researched_<slug>"
    name: Mapped[str] = mapped_column(String(200))  # the feature as asked for
    section: Mapped[str] = mapped_column(String(40))
    base_type: Mapped[str] = mapped_column(String(40))  # custom feature type it was built from
    status: Mapped[str] = mapped_column(String(20))  # active / no_evidence / retired
    spec: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)  # catalog component
    sources: Mapped[list[Any]]  # every source the search returned, with its check result
    note: Mapped[str] = mapped_column(Text, default="")
    model: Mapped[str] = mapped_column(String(100))
    prompt_version: Mapped[str] = mapped_column(String(40))
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    created_by: Mapped[str | None] = mapped_column(String(36), nullable=True)

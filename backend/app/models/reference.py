"""Global, versioned reference data: taxonomy, component catalog, rate cards, parameter sets.

Versions are immutable once written (rule 4): new prices or parameters mean a new version.
Each estimate snapshots the exact versions it used.
"""

from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import Date, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, DecimalString, IdTimestampMixin


class TaxonomyVersion(IdTimestampMixin, Base):
    __tablename__ = "taxonomy_versions"

    version: Mapped[str] = mapped_column(String(40), unique=True)
    source: Mapped[str] = mapped_column(String(200))
    data: Mapped[dict[str, Any]]


class CatalogComponent(IdTimestampMixin, Base):
    __tablename__ = "catalog_components"
    __table_args__ = (UniqueConstraint("key", "version", name="uq_catalog_components_key_version"),)

    key: Mapped[str] = mapped_column(String(100), index=True)
    version: Mapped[str] = mapped_column(String(40), index=True)
    name: Mapped[str] = mapped_column(String(200))
    category: Mapped[str] = mapped_column(String(50))
    bucket: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(Text, default="")
    source: Mapped[str] = mapped_column(String(200))
    spec: Mapped[dict[str, Any]]  # full engine CatalogComponent (task mix, efforts, drivers…)


class RateCard(IdTimestampMixin, Base):
    __tablename__ = "rate_cards"

    version: Mapped[str] = mapped_column(String(40), unique=True)
    effective_date: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20))  # draft / active / retired
    source: Mapped[str] = mapped_column(String(200))
    region: Mapped[str] = mapped_column(String(20), default="india", server_default="india")
    currency: Mapped[str] = mapped_column(String(3), default="INR", server_default="INR")
    items: Mapped[list["RateItem"]] = relationship(
        back_populates="rate_card", cascade="all, delete-orphan", order_by="RateItem.key"
    )


class RateItem(IdTimestampMixin, Base):
    __tablename__ = "rate_items"
    __table_args__ = (UniqueConstraint("rate_card_id", "key", name="uq_rate_items_card_key"),)

    rate_card_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("rate_cards.id", ondelete="CASCADE"), index=True
    )
    key: Mapped[str] = mapped_column(String(120))
    kind: Mapped[str] = mapped_column(String(30))
    unit: Mapped[str] = mapped_column(String(50))
    amount: Mapped[Decimal] = mapped_column(DecimalString)  # major units of `currency`
    currency: Mapped[str] = mapped_column(String(3))
    region: Mapped[str | None] = mapped_column(String(50))
    source: Mapped[str] = mapped_column(String(200))
    source_url: Mapped[str | None] = mapped_column(String(500))

    rate_card: Mapped[RateCard] = relationship(back_populates="items")


class ParameterSet(IdTimestampMixin, Base):
    __tablename__ = "parameter_sets"

    version: Mapped[str] = mapped_column(String(40), unique=True)
    effective_date: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20))
    region: Mapped[str] = mapped_column(String(20), default="india", server_default="india")
    data: Mapped[dict[str, Any]]  # full engine ParameterSet; each group carries its source

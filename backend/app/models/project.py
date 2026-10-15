"""Tenant tables: projects, requirements, questionnaire answers, component instances,
estimates, cost lines and assumptions. Every table carries `org_id` (rule 8)."""

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, DecimalString, IdTimestampMixin, TenantMixin


class Project(IdTimestampMixin, TenantMixin, Base):
    __tablename__ = "projects"

    name: Mapped[str] = mapped_column(String(300))
    buyer_type: Mapped[str] = mapped_column(String(20))  # govt / psu / private
    domain: Mapped[str] = mapped_column(String(100))
    mode: Mapped[str] = mapped_column(String(20), default="vendor")  # vendor / buyer
    status: Mapped[str] = mapped_column(String(30), default="draft")
    description: Mapped[str] = mapped_column(Text, default="")
    created_by: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"))

    requirements: Mapped[list["Requirement"]] = relationship(
        back_populates="project", cascade="all, delete-orphan", order_by="Requirement.code"
    )
    components: Mapped[list["ComponentInstance"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
        order_by="ComponentInstance.created_at",
    )
    answers: Mapped[list["QuestionnaireAnswer"]] = relationship(
        back_populates="project", cascade="all, delete-orphan", order_by="QuestionnaireAnswer.key"
    )


class Requirement(IdTimestampMixin, TenantMixin, Base):
    __tablename__ = "requirements"
    __table_args__ = (UniqueConstraint("project_id", "code", name="uq_requirements_project_code"),)

    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    code: Mapped[str] = mapped_column(String(30))
    text_normalised: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(30))
    clarity_score: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20))  # extracted / confirmed / rejected / edited
    source_refs: Mapped[list[Any]]  # [{clause_ref, page, document?, chunk_id?}]
    confirmed_by: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"))
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    project: Mapped[Project] = relationship(back_populates="requirements")


class QuestionnaireAnswer(IdTimestampMixin, TenantMixin, Base):
    __tablename__ = "questionnaire_answers"
    __table_args__ = (UniqueConstraint("project_id", "key", name="uq_answers_project_key"),)

    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    key: Mapped[str] = mapped_column(String(60))
    value: Mapped[Any] = mapped_column(JSON)
    source: Mapped[str] = mapped_column(String(20), default="user")
    requirement_ids: Mapped[list[Any]]

    project: Mapped[Project] = relationship(back_populates="answers")


class ComponentInstance(IdTimestampMixin, TenantMixin, Base):
    __tablename__ = "component_instances"

    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    catalog_key: Mapped[str] = mapped_column(String(100))
    label: Mapped[str | None] = mapped_column(String(200))
    size: Mapped[str] = mapped_column(String(2))
    complexity: Mapped[str] = mapped_column(String(20))
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    driver_values: Mapped[dict[str, Any]]
    requirement_ids: Mapped[list[Any]]
    status: Mapped[str] = mapped_column(String(20))  # suggested / confirmed
    confirmed_by: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"))
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    project: Mapped[Project] = relationship(back_populates="components")


class Estimate(IdTimestampMixin, TenantMixin, Base):
    """An immutable priced version. Re-pricing creates a new version (rule 4)."""

    __tablename__ = "estimates"
    __table_args__ = (
        UniqueConstraint("project_id", "version", name="uq_estimates_project_version"),
    )

    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    version: Mapped[int] = mapped_column(Integer)
    engine_version: Mapped[str] = mapped_column(String(20))
    rate_card_version: Mapped[str] = mapped_column(String(40))
    parameter_set_version: Mapped[str] = mapped_column(String(40))
    catalog_version: Mapped[str] = mapped_column(String(40))
    taxonomy_version: Mapped[str] = mapped_column(String(40))
    seed: Mapped[int] = mapped_column(BigInteger)
    as_of_date: Mapped[date] = mapped_column(Date)
    inputs_snapshot: Mapped[dict[str, Any]]
    result: Mapped[dict[str, Any]]  # EstimateResult without lines
    feasible: Mapped[bool] = mapped_column(Boolean)
    likely_paise: Mapped[int | None] = mapped_column(BigInteger)
    p10_paise: Mapped[int | None] = mapped_column(BigInteger)
    p50_paise: Mapped[int | None] = mapped_column(BigInteger)
    p90_paise: Mapped[int | None] = mapped_column(BigInteger)
    confidence: Mapped[str] = mapped_column(String(10))
    calibration_status: Mapped[str] = mapped_column(String(20))
    frozen: Mapped[bool] = mapped_column(Boolean, default=False)
    parent_estimate_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("estimates.id", ondelete="SET NULL")
    )
    created_by: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"))

    lines: Mapped[list["CostLine"]] = relationship(
        back_populates="estimate", cascade="all, delete-orphan", order_by="CostLine.sort_order"
    )
    assumptions: Mapped[list["Assumption"]] = relationship(
        back_populates="estimate", cascade="all, delete-orphan", order_by="Assumption.key"
    )


class CostLine(IdTimestampMixin, TenantMixin, Base):
    __tablename__ = "cost_lines"
    __table_args__ = (
        UniqueConstraint("estimate_id", "line_key", name="uq_cost_lines_estimate_key"),
    )

    estimate_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("estimates.id", ondelete="CASCADE"), index=True
    )
    sort_order: Mapped[int] = mapped_column(Integer)
    line_key: Mapped[str] = mapped_column(String(200))
    stage: Mapped[str] = mapped_column(String(30))
    bucket: Mapped[str] = mapped_column(String(60))
    year: Mapped[int] = mapped_column(Integer)  # 0 = build / one-off
    label: Mapped[str] = mapped_column(String(300))
    component_instance_id: Mapped[str | None] = mapped_column(String(36))
    formula_id: Mapped[str] = mapped_column(String(60))
    inputs: Mapped[dict[str, Any]]
    low_paise: Mapped[int] = mapped_column(BigInteger)
    likely_paise: Mapped[int] = mapped_column(BigInteger)
    high_paise: Mapped[int] = mapped_column(BigInteger)
    requirement_ids: Mapped[list[Any]]
    gst_percent: Mapped[Decimal] = mapped_column(DecimalString)
    derived: Mapped[bool] = mapped_column(Boolean)
    uncertainty_group: Mapped[str] = mapped_column(String(200))
    role_pd: Mapped[dict[str, Any]]
    trace: Mapped[dict[str, Any]]

    estimate: Mapped[Estimate] = relationship(back_populates="lines")


class Assumption(IdTimestampMixin, TenantMixin, Base):
    __tablename__ = "assumptions"

    estimate_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("estimates.id", ondelete="CASCADE"), index=True
    )
    key: Mapped[str] = mapped_column(String(60))
    text: Mapped[str] = mapped_column(Text)
    value: Mapped[Any] = mapped_column(JSON)
    overridden: Mapped[bool] = mapped_column(Boolean, default=False)

    estimate: Mapped[Estimate] = relationship(back_populates="assumptions")

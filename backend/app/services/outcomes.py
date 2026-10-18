"""Learn from results (brief M5): record what happened to each bid and compare it with the
estimate. The calibration report is plain arithmetic on stored integer paise; a later step will
use it to suggest parameter changes (a new, reviewed parameter-set version — never silently)."""

from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from statistics import median
from typing import Literal

from fastapi import HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.tenancy import get_owned, scoped
from app.models import Estimate, Outcome, Project, User

PERCENT = Decimal(100)
ONE_DECIMAL = Decimal("0.1")
BidResult = Literal["won", "lost", "withdrawn", "not_bid"]


class OutcomeIn(BaseModel):
    estimate_id: str | None = None  # defaults to the project's latest estimate
    bid_result: BidResult
    our_price_paise: int | None = Field(default=None, ge=0)
    l1_price_paise: int | None = Field(default=None, ge=0)
    actual_cost_paise: int | None = Field(default=None, ge=0)
    actual_effort_pd: int | None = Field(default=None, ge=0)
    notes: str = Field(default="", max_length=2000)


class OutcomeOut(OutcomeIn):
    id: str
    project_id: str
    recorded_at: datetime


class CalibrationRow(BaseModel):
    project_id: str
    project_name: str
    estimate_id: str | None
    bid_result: str
    p10_paise: int | None
    p50_paise: int | None
    p90_paise: int | None
    our_price_paise: int | None
    l1_price_paise: int | None
    actual_cost_paise: int | None
    l1_vs_estimate_percent: Decimal | None  # (L1 / P50 − 1) × 100
    l1_within_range: bool | None
    actual_vs_estimate_percent: Decimal | None


class CalibrationReport(BaseModel):
    outcomes: int
    with_l1: int
    with_actual_cost: int
    median_l1_vs_estimate_percent: Decimal | None
    l1_within_range_share_percent: Decimal | None
    median_actual_vs_estimate_percent: Decimal | None
    message: str
    rows: list[CalibrationRow]


def _out(o: Outcome) -> OutcomeOut:
    return OutcomeOut(
        id=o.id,
        project_id=o.project_id,
        recorded_at=o.updated_at,
        estimate_id=o.estimate_id,
        bid_result=o.bid_result,  # type: ignore[arg-type]
        our_price_paise=o.our_price_paise,
        l1_price_paise=o.l1_price_paise,
        actual_cost_paise=o.actual_cost_paise,
        actual_effort_pd=o.actual_effort_pd,
        notes=o.notes,
    )


def record_outcome(db: Session, user: User, project_id: str, body: OutcomeIn) -> OutcomeOut:
    """One outcome per project; recording again replaces it."""
    project = get_owned(db, Project, project_id, user.org_id)
    estimate_id = body.estimate_id
    if estimate_id is not None:
        estimate = get_owned(db, Estimate, estimate_id, user.org_id)
        if estimate.project_id != project.id:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_CONTENT, "Estimate is from another project"
            )
    else:
        latest = db.scalars(
            scoped(Estimate, user.org_id)
            .where(Estimate.project_id == project.id)
            .order_by(Estimate.version.desc())
        ).first()
        estimate_id = latest.id if latest else None
    row = db.scalars(scoped(Outcome, user.org_id).where(Outcome.project_id == project.id)).first()
    if row is None:
        row = Outcome(org_id=user.org_id, project_id=project.id)
        db.add(row)
    for key, value in body.model_dump(exclude={"estimate_id"}).items():
        setattr(row, key, value)
    row.estimate_id, row.recorded_by = estimate_id, user.id
    if project.status in {"draft", "estimated"}:
        project.status = body.bid_result
    db.commit()
    db.refresh(row)
    return _out(row)


def get_outcome(db: Session, user: User, project_id: str) -> OutcomeOut | None:
    project = get_owned(db, Project, project_id, user.org_id)
    row = db.scalars(scoped(Outcome, user.org_id).where(Outcome.project_id == project.id)).first()
    return _out(row) if row else None


def _vs(value: int | None, base: int | None) -> Decimal | None:
    if value is None or not base:
        return None
    return ((Decimal(value) / Decimal(base) - 1) * PERCENT).quantize(ONE_DECIMAL, ROUND_HALF_UP)


def _median(values: list[Decimal]) -> Decimal | None:
    return Decimal(median(values)).quantize(ONE_DECIMAL, ROUND_HALF_UP) if values else None


def calibration_report(db: Session, user: User) -> CalibrationReport:
    rows: list[CalibrationRow] = []
    for o in db.scalars(scoped(Outcome, user.org_id).order_by(Outcome.updated_at.desc())):
        project = get_owned(db, Project, o.project_id, user.org_id)
        e = db.get(Estimate, o.estimate_id) if o.estimate_id else None
        p10, p50, p90 = (e.p10_paise, e.p50_paise, e.p90_paise) if e else (None, None, None)
        within = None
        if o.l1_price_paise is not None and p10 is not None and p90 is not None:
            within = p10 <= o.l1_price_paise <= p90
        rows.append(
            CalibrationRow(
                project_id=project.id,
                project_name=project.name,
                estimate_id=o.estimate_id,
                bid_result=o.bid_result,
                p10_paise=p10,
                p50_paise=p50,
                p90_paise=p90,
                our_price_paise=o.our_price_paise,
                l1_price_paise=o.l1_price_paise,
                actual_cost_paise=o.actual_cost_paise,
                l1_vs_estimate_percent=_vs(o.l1_price_paise, p50),
                l1_within_range=within,
                actual_vs_estimate_percent=_vs(o.actual_cost_paise, p50),
            )
        )
    l1 = [r.l1_vs_estimate_percent for r in rows if r.l1_vs_estimate_percent is not None]
    actual = [
        r.actual_vs_estimate_percent for r in rows if r.actual_vs_estimate_percent is not None
    ]
    in_range = [r.l1_within_range for r in rows if r.l1_within_range is not None]
    med_l1, med_actual = _median(l1), _median(actual)
    share = (
        (Decimal(sum(in_range)) / Decimal(len(in_range)) * PERCENT).quantize(
            ONE_DECIMAL, ROUND_HALF_UP
        )
        if in_range
        else None
    )
    if med_l1 is None:
        message = "Record bid results (winning L1 price) to see how close the estimates are."
    else:
        direction = "below" if med_l1 < 0 else "above"
        message = (
            f"Winning prices were typically {abs(med_l1)}% {direction} our most-likely estimate "
            f"({len(l1)} project{'s' if len(l1) != 1 else ''})."
        )
    return CalibrationReport(
        outcomes=len(rows),
        with_l1=len(l1),
        with_actual_cost=len(actual),
        median_l1_vs_estimate_percent=med_l1,
        l1_within_range_share_percent=share,
        median_actual_vs_estimate_percent=med_actual,
        message=message,
        rows=rows,
    )

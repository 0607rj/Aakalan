"""Bid outcomes and the calibration report (learn from results). Owner only (OWNER_EMAILS)."""

from fastapi import APIRouter

from app.api.deps import DbSession, OwnerUser
from app.services.outcomes import (
    CalibrationReport,
    OutcomeIn,
    OutcomeOut,
    calibration_report,
    get_outcome,
    record_outcome,
)

router = APIRouter(tags=["outcomes"])


@router.post("/projects/{project_id}/outcome", response_model=OutcomeOut)
def post_outcome(project_id: str, body: OutcomeIn, db: DbSession, user: OwnerUser) -> OutcomeOut:
    return record_outcome(db, user, project_id, body)


@router.get("/projects/{project_id}/outcome", response_model=OutcomeOut | None)
def read_outcome(project_id: str, db: DbSession, user: OwnerUser) -> OutcomeOut | None:
    return get_outcome(db, user, project_id)


@router.get("/calibration", response_model=CalibrationReport)
def calibration(db: DbSession, user: OwnerUser) -> CalibrationReport:
    return calibration_report(db, user)

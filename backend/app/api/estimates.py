"""Estimates: calculate (new version), read, trace any line, scenarios, re-price."""

import re
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import delete as sa_delete

from app.api.deps import CurrentUser, DbSession, EditorUser, can_see_margin
from app.core.tenancy import get_owned, scoped
from app.models import CostLine, Estimate, Project, User
from app.schemas.estimate import (
    CostLineOut,
    EstimateCreate,
    EstimateOut,
    EstimateSummary,
    ScenariosOut,
    ScenariosRequest,
    TraceOut,
)
from app.services.engine.outputs import AssumptionOut, LineTrace
from app.services.engine.scenarios import Scenario
from app.services.estimates import service
from app.services.quick.service import QuickSummary
from app.services.reports.data import build_report
from app.services.reports.excel import build_boq
from app.services.reports.pdf import build_pdf

router = APIRouter(tags=["estimates"])

MARGIN_BUCKET = "commercial.margin"
MARGIN_INPUT_KEYS = ("factor_margin",)


def _redacted(line: CostLine, user: User) -> bool:
    return line.bucket == MARGIN_BUCKET and not can_see_margin(user)


def _line_out(line: CostLine, user: User) -> CostLineOut:
    hide = _redacted(line, user)
    return CostLineOut(
        id=line.id,
        line_key=line.line_key,
        stage=line.stage,
        bucket=line.bucket,
        year=line.year,
        label=line.label,
        component_instance_id=line.component_instance_id,
        formula_id=line.formula_id,
        low_paise=None if hide else line.low_paise,
        likely_paise=None if hide else line.likely_paise,
        high_paise=None if hide else line.high_paise,
        requirement_ids=line.requirement_ids,
        derived=line.derived,
        redacted=hide,
    )


def _summary(e: Estimate) -> EstimateSummary:
    return EstimateSummary(
        id=e.id,
        currency=e.inputs_snapshot["rate_card"].get("currency", "INR"),
        project_id=e.project_id,
        version=e.version,
        created_at=e.created_at,
        rate_card_version=e.rate_card_version,
        parameter_set_version=e.parameter_set_version,
        seed=e.seed,
        feasible=e.feasible,
        likely_paise=e.likely_paise,
        p10_paise=e.p10_paise,
        p50_paise=e.p50_paise,
        p90_paise=e.p90_paise,
        confidence=e.confidence,
        calibration_status=e.calibration_status,
        parent_estimate_id=e.parent_estimate_id,
    )


def _estimate_out(e: Estimate, user: User) -> EstimateOut:
    r: dict[str, Any] = e.result
    show_margin = can_see_margin(user)
    assumptions = [
        AssumptionOut(key=a.key, text=a.text, value=a.value, overridden=a.overridden)
        for a in e.assumptions
        if show_margin or a.key != "margin_percent"
    ]
    by_bucket = [g for g in r["by_bucket"] if show_margin or g["key"] != MARGIN_BUCKET]
    return EstimateOut(
        **_summary(e).model_dump(),
        engine_version=e.engine_version,
        catalog_version=e.catalog_version,
        taxonomy_version=e.taxonomy_version,
        as_of_date=e.as_of_date,
        frozen=e.frozen,
        margin_visible=show_margin,
        totals=r["totals"],
        infeasibility=r["infeasibility"],
        timeline=r["timeline"],
        confidence_detail=r["confidence"],
        calibration=r["calibration"],
        by_stage=r["by_stage"],
        by_bucket=by_bucket,
        by_year=r["by_year"],
        manpower=r["manpower"],
        top_drivers=r["top_drivers"],
        top_drivers_text=r["top_drivers_text"],
        sanity_checks=r["sanity_checks"],
        assumptions=assumptions,
        lines=[_line_out(line, user) for line in e.lines],
    )


@router.post(
    "/projects/{project_id}/estimates",
    response_model=EstimateOut,
    status_code=status.HTTP_201_CREATED,
)
def create_estimate(
    project_id: str, body: EstimateCreate, db: DbSession, user: EditorUser
) -> EstimateOut:
    project = get_owned(db, Project, project_id, user.org_id)
    inp = service.build_input(
        db,
        project,
        as_of=body.as_of_date or datetime.now(UTC).date(),
        seed=body.seed,
        rate_card_version=body.rate_card_version,
        parameter_set_version=body.parameter_set_version,
        catalog_version=body.catalog_version,
        monte_carlo_runs=body.monte_carlo_runs,
    )
    return _estimate_out(service.create_estimate(db, project, user, inp), user)


@router.get("/projects/{project_id}/estimates", response_model=list[EstimateSummary])
def list_estimates(project_id: str, db: DbSession, user: CurrentUser) -> list[EstimateSummary]:
    project = get_owned(db, Project, project_id, user.org_id)
    rows = db.scalars(
        scoped(Estimate, user.org_id)
        .where(Estimate.project_id == project.id)
        .order_by(Estimate.version.desc())
    )
    return [_summary(e) for e in rows]


@router.get("/estimates/{estimate_id}", response_model=EstimateOut)
def get_estimate(estimate_id: str, db: DbSession, user: CurrentUser) -> EstimateOut:
    return _estimate_out(get_owned(db, Estimate, estimate_id, user.org_id), user)


@router.delete("/estimates/{estimate_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_estimate(estimate_id: str, db: DbSession, user: EditorUser) -> Response:
    """Delete one estimate version (its cost lines go with it); the project stays."""
    estimate = get_owned(db, Estimate, estimate_id, user.org_id)
    db.execute(
        sa_delete(Estimate).where(Estimate.id == estimate.id, Estimate.org_id == user.org_id)
    )
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/estimates/{estimate_id}/lines/{line_id}/trace", response_model=TraceOut)
def get_trace(estimate_id: str, line_id: str, db: DbSession, user: CurrentUser) -> TraceOut:
    estimate = get_owned(db, Estimate, estimate_id, user.org_id)
    line = get_owned(db, CostLine, line_id, user.org_id)
    if line.estimate_id != estimate.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "CostLine not found")
    hide = _redacted(line, user)
    inputs = dict(line.inputs)
    if not can_see_margin(user):
        for key in MARGIN_INPUT_KEYS:
            inputs.pop(key, None)
    return TraceOut(
        estimate_id=estimate.id,
        line=_line_out(line, user),
        inputs={} if hide else inputs,
        gst_percent=str(line.gst_percent),
        trace=None if hide else LineTrace.model_validate(line.trace),
    )


@router.post("/estimates/{estimate_id}/scenarios", response_model=ScenariosOut)
def run_scenarios(
    estimate_id: str, body: ScenariosRequest, db: DbSession, user: CurrentUser
) -> ScenariosOut:
    """Side-by-side re-pricing of the same snapshot with questionnaire overrides. Not saved."""
    estimate = get_owned(db, Estimate, estimate_id, user.org_id)
    variants = body.scenarios
    if not can_see_margin(user):
        variants = [
            Scenario(
                name=sc.name,
                overrides={k: v for k, v in sc.overrides.items() if k != "margin_percent"},
            )
            for sc in variants
        ]
    return ScenariosOut(estimate_id=estimate.id, results=service.scenarios(estimate, variants))


@router.post(
    "/estimates/{estimate_id}/reprice",
    response_model=EstimateOut,
    status_code=status.HTTP_201_CREATED,
)
def reprice(estimate_id: str, db: DbSession, user: EditorUser) -> EstimateOut:
    """Re-price at current rates: a new estimate version; the original never changes."""
    estimate = get_owned(db, Estimate, estimate_id, user.org_id)
    project = get_owned(db, Project, estimate.project_id, user.org_id)
    new = service.reprice(db, project, estimate, user, datetime.now(UTC).date())
    return _estimate_out(new, user)


def _download_name(project: Project, estimate: Estimate, ext: str) -> str:
    stem = re.sub(r"[^A-Za-z0-9]+", "-", project.name).strip("-")[:60] or "estimate"
    return f"{stem}-v{estimate.version}.{ext}"


def _require_confirmed_check(summary: QuickSummary | None) -> None:
    """An estimate the independent check disagrees with is exported only after a person has
    confirmed they looked at the gap (POST /estimates/{id}/check/confirm)."""
    check = summary.independent_check if summary else None
    if check is not None and check.needs_confirmation and check.confirmed_at is None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "The independent check disagrees with this price. Look at the gap on the estimate "
            "page and confirm it before exporting.",
        )


@router.get("/estimates/{estimate_id}/report.pdf")
def report_pdf(estimate_id: str, db: DbSession, user: CurrentUser) -> Response:
    estimate = get_owned(db, Estimate, estimate_id, user.org_id)
    project = get_owned(db, Project, estimate.project_id, user.org_id)
    data = build_report(db, estimate, project, margin_visible=can_see_margin(user))
    _require_confirmed_check(data.summary)
    name = _download_name(project, estimate, "pdf")
    return Response(
        build_pdf(data),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{name}"'},
    )


@router.get("/estimates/{estimate_id}/boq.xlsx")
def boq_xlsx(estimate_id: str, db: DbSession, user: CurrentUser) -> Response:
    estimate = get_owned(db, Estimate, estimate_id, user.org_id)
    project = get_owned(db, Project, estimate.project_id, user.org_id)
    data = build_report(db, estimate, project, margin_visible=can_see_margin(user))
    _require_confirmed_check(data.summary)
    name = _download_name(project, estimate, "xlsx")
    return Response(
        build_boq(data),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{name}"'},
    )

"""Estimate use-cases: snapshot a confirmed project into an `EstimateInput`, run the engine,
persist the immutable result, re-price at current rates and run scenarios."""

import secrets
from datetime import date

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Assumption, CostLine, Estimate, Project, User
from app.services.engine.core import calculate
from app.services.engine.inputs import (
    AnswerIn,
    ComponentInstanceIn,
    EstimateInput,
    ProjectInfo,
    RequirementIn,
    SourceRef,
)
from app.services.engine.outputs import EstimateResult
from app.services.engine.scenarios import Scenario, ScenarioResult, run_scenarios
from app.services.estimates.reference_store import (
    get_catalog,
    get_parameter_set,
    get_rate_card,
    get_taxonomy,
)

PRICED_STATUSES = {"confirmed", "edited"}
SEED_BITS = 31


def _conflict(message: str) -> HTTPException:
    return HTTPException(status.HTTP_409_CONFLICT, message)


def build_input(
    db: Session,
    project: Project,
    *,
    as_of: date,
    seed: int | None = None,
    rate_card_version: str | None = None,
    parameter_set_version: str | None = None,
    monte_carlo_runs: int | None = None,
) -> EstimateInput:
    """Rule 6: refuses unless every requirement is reviewed and every component confirmed."""
    pending = [r.code for r in project.requirements if r.status == "extracted"]
    if pending:
        raise _conflict(f"Requirements awaiting review: {', '.join(pending[:10])}")
    unconfirmed = [c.catalog_key for c in project.components if c.status != "confirmed"]
    if unconfirmed:
        raise _conflict(f"Components awaiting confirmation: {', '.join(unconfirmed[:10])}")
    if not project.components:
        raise _conflict("Add and confirm at least one component before pricing.")

    reqs = [r for r in project.requirements if r.status in PRICED_STATUSES]
    priced_ids = {r.id for r in reqs}
    catalog = get_catalog(db)
    return EstimateInput(
        project=ProjectInfo(
            name=project.name, buyer_type=project.buyer_type, domain=project.domain
        ),
        as_of_date=as_of,
        seed=seed if seed is not None else secrets.randbits(SEED_BITS),
        requirements=[
            RequirementIn(
                id=r.id,
                code=r.code,
                text=r.text_normalised,
                category=r.category,
                clarity_score=r.clarity_score,
                source_refs=[SourceRef.model_validate(s) for s in r.source_refs],
            )
            for r in reqs
        ],
        components=[
            ComponentInstanceIn(
                id=c.id,
                catalog_key=c.catalog_key,
                label=c.label,
                size=c.size,  # type: ignore[arg-type]
                complexity=c.complexity,  # type: ignore[arg-type]
                quantity=c.quantity,
                requirement_ids=[x for x in c.requirement_ids if x in priced_ids],
            )
            for c in project.components
        ],
        answers=[
            AnswerIn(
                key=a.key,
                value=a.value,
                requirement_ids=[x for x in a.requirement_ids if x in priced_ids],
            )
            for a in project.answers
        ],
        taxonomy=get_taxonomy(db),
        catalog=catalog,
        rate_card=get_rate_card(db, rate_card_version, as_of),
        parameters=get_parameter_set(db, parameter_set_version, as_of),
        monte_carlo_runs=monte_carlo_runs,
    )


def persist(
    db: Session,
    project: Project,
    inp: EstimateInput,
    result: EstimateResult,
    user: User,
    parent: Estimate | None = None,
) -> Estimate:
    version = (
        db.scalar(select(func.max(Estimate.version)).where(Estimate.project_id == project.id)) or 0
    ) + 1
    summary = result.model_dump(mode="json", exclude={"lines"})
    totals = result.totals
    estimate = Estimate(
        org_id=project.org_id,
        project_id=project.id,
        version=version,
        engine_version=result.engine_version,
        rate_card_version=inp.rate_card.version,
        parameter_set_version=inp.parameters.version,
        catalog_version=inp.catalog.version,
        taxonomy_version=inp.taxonomy.version,
        seed=inp.seed,
        as_of_date=inp.as_of_date,
        inputs_snapshot=inp.model_dump(mode="json"),
        result=summary,
        feasible=result.feasible,
        likely_paise=totals.likely_paise if totals else None,
        p10_paise=totals.p10_paise if totals else None,
        p50_paise=totals.p50_paise if totals else None,
        p90_paise=totals.p90_paise if totals else None,
        confidence=result.confidence.label,
        calibration_status=result.calibration.status,
        parent_estimate_id=parent.id if parent else None,
        created_by=user.id,
    )
    for i, line in enumerate(result.lines):
        estimate.lines.append(
            CostLine(
                org_id=project.org_id,
                sort_order=i,
                line_key=line.line_key,
                stage=line.stage,
                bucket=line.bucket,
                year=line.year,
                label=line.label,
                component_instance_id=line.component_instance_id,
                formula_id=line.formula_id,
                inputs=line.model_dump(mode="json")["inputs"],
                low_paise=line.low_paise,
                likely_paise=line.likely_paise,
                high_paise=line.high_paise,
                requirement_ids=line.requirement_ids,
                gst_percent=line.gst_percent,
                derived=line.derived,
                uncertainty_group=line.uncertainty_group,
                role_pd={k: str(v) for k, v in line.role_pd.items()},
                trace=line.trace.model_dump(mode="json"),
            )
        )
    for a in result.assumptions:
        estimate.assumptions.append(
            Assumption(
                org_id=project.org_id,
                key=a.key,
                text=a.text,
                value=a.value,
                overridden=a.overridden,
            )
        )
    if project.status == "draft":
        project.status = "estimated"
    db.add(estimate)
    db.commit()
    db.refresh(estimate)
    return estimate


def priced(inp: EstimateInput) -> EstimateResult:
    """Run the engine; reference-data gaps (e.g. a role missing from the rate card) are 422s."""
    try:
        return calculate(inp)
    except KeyError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc.args[0])) from exc


def create_estimate(db: Session, project: Project, user: User, inp: EstimateInput) -> Estimate:
    return persist(db, project, inp, priced(inp), user)


def snapshot(estimate: Estimate) -> EstimateInput:
    return EstimateInput.model_validate(estimate.inputs_snapshot)


def reprice(db: Session, project: Project, estimate: Estimate, user: User, as_of: date) -> Estimate:
    """Same confirmed scope, answers and seed; current rate card, parameters and catalog.
    Creates a new version — the old estimate never changes (rule 4)."""
    old = snapshot(estimate)
    catalog = get_catalog(db)
    missing = [
        c.catalog_key
        for c in old.components
        if c.catalog_key not in {x.key for x in catalog.components}
    ]
    if missing:
        raise _conflict(f"Current catalog no longer has: {', '.join(missing)}")
    inp = old.model_copy(
        update={
            "as_of_date": as_of,
            "taxonomy": get_taxonomy(db),
            "catalog": catalog,
            "rate_card": get_rate_card(db, None, as_of),
            "parameters": get_parameter_set(db, None, as_of),
        }
    )
    inp = EstimateInput.model_validate(inp.model_dump())
    return persist(db, project, inp, priced(inp), user, parent=estimate)


def scenarios(estimate: Estimate, variants: list[Scenario]) -> list[ScenarioResult]:
    return run_scenarios(snapshot(estimate), variants)

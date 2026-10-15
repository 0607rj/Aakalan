"""Quick estimate: plain-language form -> confirmed project -> engine estimate -> plain summary.

The user's ticks and choices are the human review (rule 6): each ticked feature becomes a
confirmed requirement citing the quick-estimate form, and every component it adds is
confirmed by the same user. All numbers still come from the deterministic engine; the summary
only regroups and adds integer paise that the engine produced.
"""

from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.models import ComponentInstance, Estimate, Project, QuestionnaireAnswer, Requirement, User
from app.services.estimates import service as estimates
from app.services.quick.config import QuickConfig

FORM_DOCUMENT = "Quick estimate form"
SCALE = "scale"

# Display grouping of taxonomy stages into plain-language parts of the total.
PLAIN_GROUPS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("build", "Building the software", ("pre_build", "build")),
    ("launch", "Launch: security audit, training and go-live support", ("go_live",)),
    ("run", "Running and supporting it", ("run",)),
    ("management", "Project management", ("programme",)),
    ("taxes", "Taxes, profit margin and safety buffer", ("commercial",)),
)


class QuickRequest(BaseModel):
    name: str = Field(min_length=1, max_length=300)
    features: list[str] = Field(min_length=1)
    choices: dict[str, str | int] = {}
    deadline_months: int | None = Field(default=None, ge=1, le=60)


class PlainPart(BaseModel):
    key: str
    label: str
    amount_paise: int
    share_percent: int


class QuickSummary(BaseModel):
    project_id: str
    estimate_id: str
    name: str
    created_at: datetime
    feasible: bool
    message: str | None
    low_paise: int | None
    likely_paise: int | None
    high_paise: int | None
    planned_paise: int
    risk_allowance_paise: int | None
    build_only_paise: int
    build_months: str
    support_years: int
    parts: list[PlainPart]
    biggest_uncertainty: str | None
    features: list[str]
    indicative: bool


def _choice(cfg: QuickConfig, req: QuickRequest, key: str) -> Any:
    question = cfg.questions[key]
    value = req.choices.get(key, question.default)
    try:
        return question.option(value)
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, f"{key}: {exc}") from exc


def create_quick_estimate(db: Session, user: User, cfg: QuickConfig, req: QuickRequest) -> Estimate:
    unknown = set(req.choices) - set(cfg.questions)
    if unknown:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, f"Unknown questions: {sorted(unknown)}"
        )
    try:
        features = [cfg.feature(k) for k in dict.fromkeys(req.features)]
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc
    options = {key: _choice(cfg, req, key) for key in cfg.questions}
    size = options[SCALE].component_size
    assert size is not None, "scale options must set component_size"

    now = datetime.now(UTC)
    project = Project(
        org_id=user.org_id,
        name=req.name,
        buyer_type="govt",
        domain="quick_estimate",
        description="Created with the quick estimate form.",
        created_by=user.id,
    )
    db.add(project)
    db.flush()

    feature_req: dict[str, str] = {}
    for i, f in enumerate(features, start=1):
        r = Requirement(
            org_id=user.org_id,
            project_id=project.id,
            code=f"REQ-{i:03d}",
            text_normalised=f"{f.label}. {f.hint}",
            category="functional",
            clarity_score=cfg.requirement_clarity,
            status="confirmed",
            source_refs=[{"clause_ref": f"Feature: {f.label}", "document": FORM_DOCUMENT}],
            confirmed_by=user.id,
            confirmed_at=now,
        )
        db.add(r)
        db.flush()
        feature_req[f.key] = r.id

    component_reqs: dict[str, list[str]] = {k: [] for k in cfg.base_components}
    for key in options[SCALE].extra_components:
        component_reqs.setdefault(key, [])
    for f in features:
        for key in f.components:
            component_reqs.setdefault(key, []).append(feature_req[f.key])
    for key, req_ids in component_reqs.items():
        db.add(
            ComponentInstance(
                org_id=user.org_id,
                project_id=project.id,
                catalog_key=key,
                size=size.value,
                complexity="medium",
                quantity=1,
                driver_values={},
                requirement_ids=req_ids,
                status="confirmed",
                confirmed_by=user.id,
                confirmed_at=now,
            )
        )

    answers: dict[str, tuple[Any, list[str]]] = {}
    for option in options.values():
        for k, v in option.answers.items():
            answers[k] = (v, [])
    for f in features:
        for k, v in f.sets.items():
            answers[k] = (v, [feature_req[f.key]])
    if "ai_chatbot" not in feature_req:
        answers["chatbot_queries_per_day"] = (0, [])
    if req.deadline_months is not None:
        answers["deadline_months"] = (req.deadline_months, [])
    for k, (v, req_ids) in answers.items():
        db.add(
            QuestionnaireAnswer(
                org_id=user.org_id,
                project_id=project.id,
                key=k,
                value=v,
                source="user",
                requirement_ids=req_ids,
            )
        )
    db.flush()
    db.refresh(project)
    inp = estimates.build_input(db, project, as_of=now.date())
    return estimates.create_estimate(db, project, user, inp)


def summarise(estimate: Estimate, project: Project, cfg: QuickConfig) -> QuickSummary:
    result: dict[str, Any] = estimate.result
    stage_likely = {g["key"]: g["likely_paise"] for g in result["by_stage"]}
    planned = sum(stage_likely.values())
    parts = []
    for key, label, stages in PLAIN_GROUPS:
        amount = sum(stage_likely.get(s, 0) for s in stages)
        parts.append(
            PlainPart(
                key=key,
                label=label,
                amount_paise=amount,
                share_percent=round(100 * amount / planned) if planned else 0,
            )
        )
    years = _om_years(estimate)
    parts[2] = parts[2].model_copy(
        update={"label": f"Running and supporting it for {years} year{'s' if years != 1 else ''}"}
    )
    drivers = result["top_drivers"]
    biggest = None
    if drivers:
        top = drivers[0]
        phrase = cfg.plain_drivers.get(top["bucket"], top["name"])
        biggest = f"The biggest unknown is {phrase}."
    infeasible = result.get("infeasibility")
    timeline = result["timeline"]
    return QuickSummary(
        project_id=project.id,
        estimate_id=estimate.id,
        name=project.name,
        created_at=estimate.created_at,
        feasible=estimate.feasible,
        message=infeasible["message"] if infeasible else None,
        low_paise=estimate.p10_paise,
        likely_paise=estimate.p50_paise,
        high_paise=estimate.p90_paise,
        planned_paise=planned,
        risk_allowance_paise=(estimate.p50_paise - planned) if estimate.p50_paise else None,
        build_only_paise=sum(stage_likely.get(s, 0) for s in ("pre_build", "build", "go_live")),
        build_months=str(timeline["delivery_duration_months"]),
        support_years=years,
        parts=parts,
        biggest_uncertainty=biggest,
        features=[r.text_normalised.split(". ", 1)[0] for r in project.requirements],
        indicative=estimate.calibration_status == "uncalibrated",
    )


def _om_years(estimate: Estimate) -> int:
    for a in estimate.inputs_snapshot.get("answers", []):
        if a["key"] == "om_years":
            return int(a["value"])
    return int(estimate.inputs_snapshot["parameters"]["defaults"]["values"]["om_years"])

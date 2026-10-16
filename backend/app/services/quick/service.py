"""Quick estimate: plain-language form -> confirmed project -> engine estimate -> plain summary.

The user's ticks and choices are the human review (rule 6): each ticked feature becomes a
confirmed requirement citing the quick-estimate form, and every component it adds is
confirmed by the same user. All numbers still come from the deterministic engine; the summary
only regroups and adds integer paise that the engine produced.
"""

from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from typing import Any

from fastapi import HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.tenancy import get_owned
from app.models import (
    ComponentInstance,
    Document,
    Estimate,
    Project,
    QuestionnaireAnswer,
    Requirement,
    User,
)
from app.services.engine.core import calculate
from app.services.engine.inputs import (
    AnswerIn,
    ComponentInstanceIn,
    EstimateInput,
    ProjectInfo,
    RequirementIn,
    SourceRef,
)
from app.services.engine.reference import Size
from app.services.estimates import service as estimates
from app.services.estimates.reference_store import (
    get_catalog,
    get_parameter_set,
    get_rate_card,
    get_taxonomy,
)
from app.services.extraction.merge import project_extraction
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


# Numbers the form may set directly (pre-filled from the tender, editable by the user).
OVERRIDABLE = frozenset(
    {
        "users_total",
        "peak_concurrent_users",
        "om_years",
        "deadline_months",
        "languages",
        "chatbot_queries_per_day",
        "documents_per_month",
        "emd_paise",
        "pbg_percent",
    }
)


class QuickRequest(BaseModel):
    name: str = Field(min_length=1, max_length=300)
    features: list[str] = Field(min_length=1)
    choices: dict[str, str | int] = {}
    deadline_months: int | None = Field(default=None, ge=1, le=60)
    document_id: str | None = None  # a document uploaded via POST /documents
    overrides: dict[str, int | float] = {}


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


def _evidence_refs(found: dict[str, Any] | None, filename: str) -> list[dict[str, Any]]:
    if not found:
        return []
    return [
        {
            "clause_ref": ev["clause_ref"] or f"Page {ev['page']}",
            "page": ev["page"],
            "document": ev.get("document") or filename,
        }
        for ev in found["evidence"]
    ]


def _quote(found: dict[str, Any] | None) -> str:
    if not found or not found["evidence"]:
        return ""
    return f' Tender says: "{found["evidence"][0]["quote"]}"'


def _reset(db: Session, project: Project) -> None:
    """Recalculating from the same upload replaces the previous mapping (estimates keep their
    own snapshots, so earlier versions are unaffected)."""
    for row in [*project.requirements, *project.components, *project.answers]:
        db.delete(row)
    db.flush()
    db.refresh(project)


@dataclass
class PlannedRequirement:
    text: str
    category: str
    refs: list[dict[str, Any]]


@dataclass
class QuickPlan:
    """Everything a quick estimate creates, before it touches the database. The same plan is
    persisted for a real estimate and converted in memory for "what if" pricing."""

    requirements: dict[str, PlannedRequirement] = field(default_factory=dict)
    components: list[tuple[str, Size, list[str]]] = field(default_factory=list)
    answers: dict[str, tuple[Any, list[str]]] = field(default_factory=dict)


def _unprocessable(message: str) -> HTTPException:
    return HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, message)


def plan_quick(
    cfg: QuickConfig, req: QuickRequest, extraction: dict[str, Any] | None, filename: str
) -> QuickPlan:
    unknown = set(req.choices) - set(cfg.questions)
    if unknown:
        raise _unprocessable(f"Unknown questions: {sorted(unknown)}")
    bad_overrides = set(req.overrides) - OVERRIDABLE
    if bad_overrides:
        raise _unprocessable(f"Unknown values: {sorted(bad_overrides)}")
    try:
        features = [cfg.feature(k) for k in dict.fromkeys(req.features)]
    except ValueError as exc:
        raise _unprocessable(str(exc)) from exc
    options = {key: _choice(cfg, req, key) for key in cfg.questions}
    size = options[SCALE].component_size
    assert size is not None, "scale options must set component_size"
    extraction = extraction or {}
    found_features = {f["key"]: f for f in extraction.get("features", [])}
    found_choices: dict[str, Any] = extraction.get("choices", {})
    found_numbers: dict[str, Any] = extraction.get("numbers", {})

    plan = QuickPlan()

    def requirement(text: str, category: str, refs: list[dict[str, Any]]) -> str:
        key = f"REQ-{len(plan.requirements) + 1:03d}"
        plan.requirements[key] = PlannedRequirement(text, category, refs)
        return key

    feature_req: dict[str, str] = {}
    for f in features:
        found = found_features.get(f.key)
        refs = _evidence_refs(found, filename) or [
            {"clause_ref": f"Feature: {f.label}", "document": FORM_DOCUMENT}
        ]
        feature_req[f.key] = requirement(f"{f.label}. {f.hint}{_quote(found)}", "functional", refs)

    component_reqs: dict[str, list[str]] = {k: [] for k in cfg.base_components}
    for key in options[SCALE].extra_components:
        component_reqs.setdefault(key, [])
    for f in features:
        for key in f.components:
            component_reqs.setdefault(key, []).append(feature_req[f.key])
    plan.components = [(key, size, reqs) for key, reqs in component_reqs.items()]

    def cited(found: dict[str, Any] | None, label: str) -> list[str]:
        """Requirement keys proving a value, when the value the user kept came from the tender."""
        refs = _evidence_refs(found, filename)
        return [requirement(f"{label}.{_quote(found)}", "NFR", refs)] if refs else []

    for key, option in options.items():
        found = found_choices.get(key)
        kept = found is not None and found["value"] == option.value
        ids = cited(found, cfg.questions[key].label) if kept else []
        for k, v in option.answers.items():
            plan.answers[k] = (v, ids)
    for f in features:
        for k, v in f.sets.items():
            plan.answers[k] = (v, [feature_req[f.key]])
    if "ai_chatbot" not in feature_req:
        plan.answers["chatbot_queries_per_day"] = (0, [])
    overrides: dict[str, Any] = dict(req.overrides)
    if req.deadline_months is not None:
        overrides.setdefault("deadline_months", req.deadline_months)
    for k, v in overrides.items():
        found = found_numbers.get(k)
        kept = found is not None and found["value"] == v
        plan.answers[k] = (v, cited(found, k.replace("_", " ").capitalize()) if kept else [])
    return plan


def _document_context(
    db: Session, user: User, document_id: str | None
) -> tuple[Document | None, dict[str, Any] | None, str]:
    if not document_id:
        return None, None, FORM_DOCUMENT
    doc = get_owned(db, Document, document_id, user.org_id)
    project = get_owned(db, Project, doc.project_id, user.org_id)
    merged = project_extraction(db, project).extraction  # all files of the project
    return doc, merged.model_dump(mode="json") if merged else None, doc.filename


def create_quick_estimate(db: Session, user: User, cfg: QuickConfig, req: QuickRequest) -> Estimate:
    doc, extraction, filename = _document_context(db, user, req.document_id)
    plan = plan_quick(cfg, req, extraction, filename)
    now = datetime.now(UTC)
    if doc is not None:
        project = get_owned(db, Project, doc.project_id, user.org_id)
        _reset(db, project)
        project.name = req.name
    else:
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

    ids: dict[str, str] = {}
    for code, planned in plan.requirements.items():
        row = Requirement(
            org_id=user.org_id,
            project_id=project.id,
            code=code,
            text_normalised=planned.text,
            category=planned.category,
            clarity_score=cfg.requirement_clarity,
            status="confirmed",
            source_refs=planned.refs,
            confirmed_by=user.id,
            confirmed_at=now,
        )
        db.add(row)
        db.flush()
        ids[code] = row.id
    for key, size, reqs in plan.components:
        db.add(
            ComponentInstance(
                org_id=user.org_id,
                project_id=project.id,
                catalog_key=key,
                size=size.value,
                complexity="medium",
                quantity=1,
                driver_values={},
                requirement_ids=[ids[r] for r in reqs],
                status="confirmed",
                confirmed_by=user.id,
                confirmed_at=now,
            )
        )
    for k, (v, reqs) in plan.answers.items():
        db.add(
            QuestionnaireAnswer(
                org_id=user.org_id,
                project_id=project.id,
                key=k,
                value=v,
                source="user",
                requirement_ids=[ids[r] for r in reqs],
            )
        )
    db.flush()
    db.refresh(project)
    inp = estimates.build_input(db, project, as_of=now.date())
    return estimates.create_estimate(db, project, user, inp)


# --- price impact of the open questions ----------------------------------------------------


class OptionPrice(BaseModel):
    value: str | int
    label: str
    likely_paise: int | None  # None when that choice makes the deadline infeasible


class QuestionImpact(BaseModel):
    key: str
    label: str
    impact_paise: int  # spread of the most-likely total across the options
    options: list[OptionPrice]


def plan_to_input(
    plan: QuickPlan, name: str, reference: dict[str, Any], as_of: date, seed: int, runs: int
) -> EstimateInput:
    """The plan as an engine snapshot, without writing anything (ids are the plan's keys)."""
    return EstimateInput(
        project=ProjectInfo(name=name, buyer_type="govt", domain="quick_estimate"),
        as_of_date=as_of,
        seed=seed,
        requirements=[
            RequirementIn(
                id=code,
                code=code,
                text=r.text,
                category=r.category,
                clarity_score=reference["clarity"],
                source_refs=[SourceRef.model_validate(ref) for ref in r.refs],
            )
            for code, r in plan.requirements.items()
        ],
        components=[
            ComponentInstanceIn(id=f"C{i:03d}", catalog_key=key, size=size, requirement_ids=reqs)
            for i, (key, size, reqs) in enumerate(plan.components, start=1)
        ],
        answers=[
            AnswerIn(key=k, value=v, requirement_ids=reqs) for k, (v, reqs) in plan.answers.items()
        ],
        taxonomy=reference["taxonomy"],
        catalog=reference["catalog"],
        rate_card=reference["rate_card"],
        parameters=reference["parameters"],
        monte_carlo_runs=runs,
    )


def question_impact(
    db: Session, user: User, cfg: QuickConfig, req: QuickRequest
) -> list[QuestionImpact]:
    """Re-price the form once per option of every question and rank questions by how much the
    most-likely total moves (brief: ask the questions that change the price most, first)."""
    _, extraction, filename = _document_context(db, user, req.document_id)
    today = datetime.now(UTC).date()
    reference = {
        "taxonomy": get_taxonomy(db),
        "catalog": get_catalog(db),
        "rate_card": get_rate_card(db, None, today),
        "parameters": get_parameter_set(db, None, today),
        "clarity": cfg.requirement_clarity,
    }
    out = []
    for key, question in cfg.questions.items():
        if key == "support_years" and "om_years" in req.overrides:
            continue
        prices = []
        for option in question.options:
            variant = req.model_copy(update={"choices": {**req.choices, key: option.value}})
            plan = plan_quick(cfg, variant, extraction, filename)
            inp = plan_to_input(
                plan, req.name, reference, today, cfg.impact.seed, cfg.impact.monte_carlo_runs
            )
            totals = calculate(inp).totals
            prices.append(
                OptionPrice(
                    value=option.value,
                    label=option.label,
                    likely_paise=totals.p50_paise if totals else None,
                )
            )
        known = [p.likely_paise for p in prices if p.likely_paise is not None]
        out.append(
            QuestionImpact(
                key=key,
                label=question.label,
                impact_paise=(max(known) - min(known)) if known else 0,
                options=prices,
            )
        )
    out.sort(key=lambda q: -q.impact_paise)
    return out


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

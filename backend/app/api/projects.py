"""Projects and their reviewed inputs: requirements, questionnaire answers, components."""

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Response, status
from pydantic import ValidationError
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession, EditorUser, can_see_margin
from app.core.tenancy import get_owned, scoped
from app.models import ComponentInstance, Project, QuestionnaireAnswer, Requirement
from app.schemas.project import (
    AnswerIn,
    CatalogComponentOut,
    CatalogOut,
    ComponentOut,
    ComponentsPut,
    ConfirmRequest,
    ProjectCreate,
    ProjectOut,
    ProjectUpdate,
    QuestionnaireField,
    QuestionnaireOut,
    QuestionnairePut,
    RequirementCreate,
    RequirementOut,
    RequirementUpdate,
)
from app.services.engine.context import resolve_questionnaire
from app.services.engine.inputs import QUESTIONNAIRE_KEYS, Questionnaire
from app.services.engine.inputs import AnswerIn as EngineAnswer
from app.services.estimates.reference_store import get_catalog, get_parameter_set

router = APIRouter(tags=["projects"])

RESTRICTED_KEYS = frozenset({"margin_percent"})


def _now() -> datetime:
    return datetime.now(UTC)


# --- projects --------------------------------------------------------------------------------


@router.post("/projects", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
def create_project(body: ProjectCreate, db: DbSession, user: EditorUser) -> Project:
    project = Project(org_id=user.org_id, created_by=user.id, **body.model_dump())
    db.add(project)
    db.commit()
    return project


@router.get("/projects", response_model=list[ProjectOut])
def list_projects(db: DbSession, user: CurrentUser) -> list[Project]:
    return list(db.scalars(scoped(Project, user.org_id).order_by(Project.created_at.desc())))


@router.get("/projects/{project_id}", response_model=ProjectOut)
def get_project(project_id: str, db: DbSession, user: CurrentUser) -> Project:
    return get_owned(db, Project, project_id, user.org_id)


@router.patch("/projects/{project_id}", response_model=ProjectOut)
def update_project(
    project_id: str, body: ProjectUpdate, db: DbSession, user: EditorUser
) -> Project:
    project = get_owned(db, Project, project_id, user.org_id)
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(project, key, value)
    db.commit()
    return project


# --- requirements ----------------------------------------------------------------------------


@router.get("/projects/{project_id}/requirements", response_model=list[RequirementOut])
def list_requirements(project_id: str, db: DbSession, user: CurrentUser) -> list[Requirement]:
    return get_owned(db, Project, project_id, user.org_id).requirements


@router.post(
    "/projects/{project_id}/requirements",
    response_model=RequirementOut,
    status_code=status.HTTP_201_CREATED,
)
def create_requirement(
    project_id: str, body: RequirementCreate, db: DbSession, user: EditorUser
) -> Requirement:
    """Manual entry by a user counts as reviewed, so it is created as `confirmed`."""
    project = get_owned(db, Project, project_id, user.org_id)
    codes = {r.code for r in project.requirements}
    code = body.code or f"REQ-{len(codes) + 1:03d}"
    while code in codes:
        code = f"REQ-{int(code.rsplit('-', 1)[-1]) + 1:03d}" if code[-1].isdigit() else code + "-1"
    req = Requirement(
        org_id=user.org_id,
        project_id=project.id,
        code=code,
        text_normalised=body.text,
        category=body.category,
        clarity_score=body.clarity_score,
        status="confirmed",
        source_refs=[s.model_dump(mode="json") for s in body.source_refs],
        confirmed_by=user.id,
        confirmed_at=_now(),
    )
    db.add(req)
    db.commit()
    return req


@router.patch("/requirements/{requirement_id}", response_model=RequirementOut)
def update_requirement(
    requirement_id: str, body: RequirementUpdate, db: DbSession, user: EditorUser
) -> Requirement:
    req = get_owned(db, Requirement, requirement_id, user.org_id)
    changes = body.model_dump(exclude_unset=True, exclude={"status"})
    if "text" in changes:
        req.text_normalised = changes.pop("text")
        req.status = "edited"
    if "source_refs" in changes:
        req.source_refs = [s.model_dump(mode="json") for s in body.source_refs or []]
        changes.pop("source_refs")
    for key, value in changes.items():
        setattr(req, key, value)
    if body.status is not None:
        req.status = body.status
    req.confirmed_by, req.confirmed_at = user.id, _now()
    db.commit()
    return req


@router.delete("/requirements/{requirement_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_requirement(requirement_id: str, db: DbSession, user: EditorUser) -> Response:
    db.delete(get_owned(db, Requirement, requirement_id, user.org_id))
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/projects/{project_id}/requirements/confirm", response_model=list[RequirementOut])
def confirm_requirements(
    project_id: str, body: ConfirmRequest, db: DbSession, user: EditorUser
) -> list[Requirement]:
    project = get_owned(db, Project, project_id, user.org_id)
    wanted = set(body.requirement_ids) if body.requirement_ids is not None else None
    for req in project.requirements:
        if (wanted is None and req.status == "extracted") or (wanted and req.id in wanted):
            req.status = "confirmed"
            req.confirmed_by, req.confirmed_at = user.id, _now()
    db.commit()
    return project.requirements


# --- questionnaire ---------------------------------------------------------------------------


@router.get("/projects/{project_id}/questionnaire", response_model=QuestionnaireOut)
def get_questionnaire(project_id: str, db: DbSession, user: CurrentUser) -> QuestionnaireOut:
    project = get_owned(db, Project, project_id, user.org_id)
    params = get_parameter_set(db, None, _now().date())
    answers = {a.key: a for a in project.answers}
    schema = Questionnaire.model_json_schema()
    show_margin = can_see_margin(user)
    fields = []
    for key in QUESTIONNAIRE_KEYS:
        ans = answers.get(key)
        hidden = key in RESTRICTED_KEYS and not show_margin
        default = params.defaults.values.get(key)
        fields.append(
            QuestionnaireField(
                key=key,
                title=schema["properties"][key].get("title", key),
                schema_=schema["properties"][key],
                default=None if hidden else default,
                value=None if hidden else (ans.value if ans else default),
                source="user" if ans else "default",
                requirement_ids=ans.requirement_ids if ans else [],
                restricted=key in RESTRICTED_KEYS,
            )
        )
    return QuestionnaireOut(parameter_set_version=params.version, fields=fields)


@router.put("/projects/{project_id}/questionnaire", response_model=QuestionnaireOut)
def put_questionnaire(
    project_id: str, body: QuestionnairePut, db: DbSession, user: EditorUser
) -> QuestionnaireOut:
    """Replace the project's answers. Keys left out fall back to parameter-set defaults.
    Restricted keys (margin) can only be changed by finance/admin and are kept otherwise."""
    project = get_owned(db, Project, project_id, user.org_id)
    given = {a.key: a for a in body.answers}
    unknown = set(given) - set(QUESTIONNAIRE_KEYS)
    if unknown:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, f"Unknown keys: {sorted(unknown)}"
        )
    if not can_see_margin(user) and RESTRICTED_KEYS & set(given):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only finance or admin can set margin")
    req_ids = {r.id for r in project.requirements}
    for a in body.answers:
        if set(a.requirement_ids) - req_ids:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_CONTENT, f"{a.key}: unknown requirement"
            )
    existing = {a.key: a for a in project.answers}
    if not can_see_margin(user):
        for key in RESTRICTED_KEYS & set(existing):  # keep the finance-set value
            row = existing[key]
            given[key] = AnswerIn(key=key, value=row.value, requirement_ids=row.requirement_ids)
    params = get_parameter_set(db, None, _now().date())
    try:
        resolve_questionnaire(
            [EngineAnswer(key=k, value=a.value) for k, a in given.items()],
            params.defaults.values,
        )
    except (ValidationError, ValueError) as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, _errors(exc)) from exc
    for key, row in existing.items():
        if key not in given:
            db.delete(row)
    for key, a in given.items():
        current = existing.get(key)
        if current is None:
            db.add(
                QuestionnaireAnswer(
                    org_id=user.org_id,
                    project_id=project.id,
                    key=key,
                    value=a.value,
                    source="user",
                    requirement_ids=a.requirement_ids,
                )
            )
        else:
            current.value, current.requirement_ids = a.value, a.requirement_ids
    db.commit()
    db.refresh(project)
    return get_questionnaire(project_id, db, user)


def _errors(exc: Exception) -> Any:
    if isinstance(exc, ValidationError):
        return [{"loc": e["loc"], "msg": e["msg"]} for e in exc.errors()]
    return str(exc)


# --- catalog and components ------------------------------------------------------------------


@router.get("/catalog", response_model=CatalogOut)
def catalog(db: DbSession, user: CurrentUser) -> CatalogOut:
    cat = get_catalog(db)
    return CatalogOut(
        version=cat.version,
        components=[
            CatalogComponentOut(
                key=c.key,
                name=c.name,
                category=c.category,
                bucket=c.bucket,
                description=c.description,
                base_effort_pd={k.value: str(v) for k, v in c.base_effort_pd.items()},
                applicable_drivers=[d.value for d in c.applicable_drivers],
                tags=list(c.tags),
                licensable=c.licence is not None,
                source=c.source,
            )
            for c in cat.components
        ],
    )


@router.get("/projects/{project_id}/components", response_model=list[ComponentOut])
def list_components(project_id: str, db: DbSession, user: CurrentUser) -> list[ComponentInstance]:
    return get_owned(db, Project, project_id, user.org_id).components


@router.put("/projects/{project_id}/components", response_model=list[ComponentOut])
def put_components(
    project_id: str, body: ComponentsPut, db: DbSession, user: EditorUser
) -> list[ComponentInstance]:
    """Replace the component mapping; saving it is the user's confirmation (rule 6)."""
    project = get_owned(db, Project, project_id, user.org_id)
    keys = {c.key for c in get_catalog(db).components}
    req_ids = {r.id for r in project.requirements}
    for c in body.components:
        if c.catalog_key not in keys:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_CONTENT, f"Unknown component {c.catalog_key}"
            )
        if set(c.requirement_ids) - req_ids:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_CONTENT, f"{c.catalog_key}: unknown requirement"
            )
    for row in list(project.components):
        db.delete(row)
    db.flush()
    now = _now()
    for c in body.components:
        db.add(
            ComponentInstance(
                org_id=user.org_id,
                project_id=project.id,
                catalog_key=c.catalog_key,
                label=c.label,
                size=c.size.value,
                complexity=c.complexity.value,
                quantity=c.quantity,
                driver_values={},
                requirement_ids=c.requirement_ids,
                status="confirmed",
                confirmed_by=user.id,
                confirmed_at=now,
            )
        )
    db.commit()
    return list(
        db.scalars(
            select(ComponentInstance)
            .where(ComponentInstance.project_id == project.id)
            .order_by(ComponentInstance.created_at)
        )
    )

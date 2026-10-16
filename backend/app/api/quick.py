"""Quick estimate for non-technical users: tick features, answer a few plain questions, get a
plain-language cost summary. The detailed estimate stays available under /estimates/{id}."""

from fastapi import APIRouter, status
from pydantic import BaseModel

from app.api.deps import CurrentUser, DbSession, EditorUser
from app.core.tenancy import get_owned, scoped
from app.models import Estimate, Project
from app.services.quick.config import quick_config
from app.services.quick.service import (
    QuestionImpact,
    QuickRequest,
    QuickSummary,
    create_quick_estimate,
    question_impact,
    summarise,
)

router = APIRouter(tags=["quick estimate"])


class OptionOut(BaseModel):
    value: str | int
    label: str
    hint: str


class QuestionOut(BaseModel):
    key: str
    label: str
    default: str | int
    options: list[OptionOut]


class FeatureOut(BaseModel):
    key: str
    label: str
    hint: str


class QuickOptions(BaseModel):
    features: list[FeatureOut]
    questions: list[QuestionOut]


@router.get("/quick-estimate/options", response_model=QuickOptions)
def options(_user: CurrentUser) -> QuickOptions:
    cfg = quick_config()
    return QuickOptions(
        features=[FeatureOut(key=f.key, label=f.label, hint=f.hint) for f in cfg.features],
        questions=[
            QuestionOut(
                key=key,
                label=q.label,
                default=q.default,
                options=[OptionOut(value=o.value, label=o.label, hint=o.hint) for o in q.options],
            )
            for key, q in cfg.questions.items()
        ],
    )


@router.post("/quick-estimates", response_model=QuickSummary, status_code=status.HTTP_201_CREATED)
def create(body: QuickRequest, db: DbSession, user: EditorUser) -> QuickSummary:
    estimate = create_quick_estimate(db, user, quick_config(), body)
    project = get_owned(db, Project, estimate.project_id, user.org_id)
    return summarise(estimate, project, quick_config())


@router.get("/quick-estimates", response_model=list[QuickSummary])
def list_summaries(db: DbSession, user: CurrentUser) -> list[QuickSummary]:
    """Latest estimate of every project, newest first."""
    latest: dict[str, Estimate] = {}
    for e in db.scalars(scoped(Estimate, user.org_id).order_by(Estimate.created_at.desc())):
        latest.setdefault(e.project_id, e)
    out = []
    for e in latest.values():
        project = get_owned(db, Project, e.project_id, user.org_id)
        out.append(summarise(e, project, quick_config()))
    return out


@router.get("/estimates/{estimate_id}/summary", response_model=QuickSummary)
def summary(estimate_id: str, db: DbSession, user: CurrentUser) -> QuickSummary:
    estimate = get_owned(db, Estimate, estimate_id, user.org_id)
    project = get_owned(db, Project, estimate.project_id, user.org_id)
    return summarise(estimate, project, quick_config())


@router.post("/quick-estimate/impact", response_model=list[QuestionImpact])
def impact(body: QuickRequest, db: DbSession, user: CurrentUser) -> list[QuestionImpact]:
    """Which questions change the price most for this form (nothing is saved)."""
    return question_impact(db, user, quick_config(), body)

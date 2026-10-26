"""Quick estimate for non-technical users: tick features, answer a few plain questions, get a
plain-language cost summary. The detailed estimate stays available under /estimates/{id}."""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.api.deps import CurrentUser, DbSession, EditorUser, can_see_margin
from app.core.tenancy import get_owned, scoped
from app.llm.client import LLMNotConfiguredError, LLMRefusedError
from app.models import Estimate, Project, ResearchedComponent, SharedResearchedComponent
from app.services.extraction.describe import Suggestion, suggest_features
from app.services.quick import second_opinion
from app.services.quick.config import quick_config
from app.services.quick.prefill import form_country, form_questions
from app.services.quick.second_opinion import SecondOpinionOut
from app.services.quick.service import (
    AI_USE,
    PricedOption,
    QuestionImpact,
    QuickRequest,
    QuickSummary,
    confirm_check,
    create_quick_estimate,
    feature_level_options,
    priced_options,
    question_impact,
    standard_blocks,
    summarise,
    summary_for,
)
from app.services.quick.stories import DraftIn, DraftOut, draft_stories
from app.services.research.library import shared_blocks
from app.services.research.service import ai_available, catalog_sections, research_rows
from app.services.settings import company_settings

router = APIRouter(tags=["quick estimate"])


class OptionOut(BaseModel):
    value: str | int
    label: str
    hint: str
    unsure: bool = False  # "Not sure": the usual answer, with a wider range
    left_out: bool = False  # "Not sure" that leaves the item out and quotes it as an option
    max_users: int | None = None  # scale options: the most users it covers (None = no limit)
    add_features: dict[str, str | None] = {}  # features this answer adds (and their level)
    feature_level: str | None = None  # default level of every feature (MVP / full product)
    # scale options: the people online at once this band assumes (the form's default)
    peak_online: int | None = None


def _int_or_none(value: object) -> int | None:
    return int(value) if isinstance(value, int | float | str) and str(value).isdigit() else None


class QuestionOut(BaseModel):
    key: str
    label: str
    default: str | int
    options: list[OptionOut]
    group: str = "main"  # main = one screen each; detail = the optional details screen
    only_with_features: list[str] = []  # ask only when one of these features is chosen
    only_with_custom_types: list[str] = []  # ... or a custom feature of one of these types
    hide_when: dict[str, list[str | int]] = {}  # hidden when another answer is one of these
    default_by: dict[str, dict[str, str | int]] = {}  # default that follows another answer
    on_upload: str = "ask"  # document = on file upload, the document decides; never asked
    answered_by_number: str | None = None  # not asked when this number is known
    must_choose: bool = False  # nothing pre-selected: the user must pick an answer


class LevelOut(BaseModel):
    key: str  # basic / standard / advanced
    label: str
    hint: str  # what this level means for the feature


class FeatureOut(BaseModel):
    key: str
    label: str
    hint: str
    levels: list[LevelOut] = []  # empty: the feature comes in one size only
    hidden: bool = False  # not ticked: added by a question's answer (e.g. a mobile app)


class ProjectTypeOut(BaseModel):
    key: str
    label: str
    hint: str
    features: list[str]  # shown first (empty = every feature)
    suggested: list[str]  # ticked to start with


class CustomTypeOut(BaseModel):
    key: str
    label: str


class CountryOut(BaseModel):
    key: str
    label: str
    currency: str


class ScopeItemOut(BaseModel):
    key: str
    label: str
    note: str = ""  # what is and is not priced
    partly_priced: bool = False  # part of the work is not priced (no evidence)


class ScopeGroupOut(BaseModel):
    key: str
    label: str
    feature: str | None  # shown when this feature is ticked; None = every project
    items: list[ScopeItemOut]


class ResearchedOut(BaseModel):
    """A feature researched before, by this company or shared by the library (services/
    research): ticked, it is sent as a custom feature with this catalog key, so it is priced
    by the saved block, not searched again."""

    catalog_key: str
    name: str
    category: str  # custom feature type it was built from
    section: str  # catalog section key (web, mobile, ...)
    section_label: str


class QuickOptions(BaseModel):
    country: str
    countries: list[CountryOut]
    project_types: list[ProjectTypeOut]
    features: list[FeatureOut]
    default_level: str
    questions: list[QuestionOut]
    custom_feature_types: list[CustomTypeOut]
    scope: list[ScopeGroupOut] = []  # what else a feature may need (QuickRequest.scope)
    researched: list[ResearchedOut] = []  # the company's researched features, by section
    # "Not mentioned: do you need these?": features often needed (at most 8), in order
    commonly_needed: list[str] = []


def researched_options(db: DbSession, org_id: str, types: set[str]) -> list[ResearchedOut]:
    """Researched features to offer: the organisation's active ones and the shared library's
    (each key once, none the organisation retired), in catalog section order, then by name."""
    sections = catalog_sections()
    order = {k: i for i, k in enumerate(sections)}
    own = research_rows(db, org_id)
    seen = {r.key for r in own if r.status != "active"}
    rows: list[ResearchedComponent | SharedResearchedComponent] = []
    candidates: list[ResearchedComponent | SharedResearchedComponent] = [
        *(r for r in own if r.status == "active" and r.spec),
        *shared_blocks(db),
    ]
    for r in candidates:
        if r.key not in seen and r.base_type in types:
            rows.append(r)
            seen.add(r.key)
    rows.sort(key=lambda r: (order.get(r.section, len(order)), r.name.lower()))
    return [
        ResearchedOut(
            catalog_key=r.key,
            name=r.name,
            category=r.base_type,
            section=r.section,
            section_label=sections.get(r.section, r.section).split(":", 1)[0],
        )
        for r in rows
    ]


@router.get("/quick-estimate/options", response_model=QuickOptions)
def options(db: DbSession, user: CurrentUser, country: str = "india") -> QuickOptions:
    """Form options; hosting choices are limited to those available in `country`, and the
    AI-use question defaults to the company's saved AI level."""
    cfg = quick_config()
    ai_level = company_settings(db, user.org_id).team_ai_maturity
    enabled = {k: c for k, c in cfg.countries.items() if c.enabled}
    country = form_country(cfg, country)
    return QuickOptions(
        country=country,
        countries=[
            CountryOut(key=k, label=c.label, currency=c.currency) for k, c in enabled.items()
        ],
        features=[
            FeatureOut(
                key=f.key,
                label=f.label,
                hint=f.hint,
                levels=[
                    LevelOut(key=k, label=cfg.sizing.levels[k].label, hint=hint)
                    for k, hint in feature_level_options(cfg, f).items()
                ]
                if f.levels
                else [],
                hidden=f.hidden,
            )
            for f in cfg.features
        ],
        default_level=cfg.sizing.default_level,
        scope=[
            ScopeGroupOut(
                key=g.key,
                label=g.label,
                feature=g.feature,
                items=[
                    ScopeItemOut(
                        key=i.key, label=i.label, note=i.note, partly_priced=i.partly_priced
                    )
                    for i in g.items
                ],
            )
            for g in cfg.scope
        ],
        project_types=[ProjectTypeOut(**t.model_dump()) for t in cfg.project_types],
        questions=[
            QuestionOut(
                key=key,
                label=q.label,
                default=ai_level if key == AI_USE and ai_level is not None else q.default,
                options=[
                    OptionOut(
                        value=o.value,
                        label=o.label,
                        hint=o.hint,
                        unsure=o.unsure,
                        left_out=bool(o.left_out),
                        add_features=dict(o.add_features),
                        feature_level=o.feature_level,
                        max_users=o.max_users,
                        peak_online=_int_or_none(o.answers.get("peak_concurrent_users")),
                    )
                    for o in q.options
                ],
                only_with_features=q.only_with_features,
                only_with_custom_types=q.only_with_custom_types,
                hide_when=q.hide_when,
                default_by=q.default_by,
                group=q.group,
                on_upload=q.on_upload,
                answered_by_number=q.answered_by_number,
                must_choose=q.must_choose,
            )
            for key, q in form_questions(cfg, country).items()
        ],
        custom_feature_types=[
            CustomTypeOut(key=k, label=t.label) for k, t in cfg.custom_feature_types.items()
        ],
        researched=researched_options(db, user.org_id, set(cfg.custom_feature_types)),
        commonly_needed=cfg.commonly_needed,
    )


@router.post("/quick-estimates", response_model=QuickSummary, status_code=status.HTTP_201_CREATED)
def create(body: QuickRequest, db: DbSession, user: EditorUser) -> QuickSummary:
    estimate = create_quick_estimate(db, user, quick_config(), body)
    project = get_owned(db, Project, estimate.project_id, user.org_id)
    return summary_for(db, estimate, project, quick_config(), margin_visible=can_see_margin(user))


@router.get("/quick-estimates", response_model=list[QuickSummary])
def list_summaries(db: DbSession, user: CurrentUser) -> list[QuickSummary]:
    """Latest estimate of every project, newest first."""
    latest: dict[str, Estimate] = {}
    for e in db.scalars(scoped(Estimate, user.org_id).order_by(Estimate.created_at.desc())):
        latest.setdefault(e.project_id, e)
    out = []
    for e in latest.values():
        project = get_owned(db, Project, e.project_id, user.org_id)
        out.append(summarise(e, project, quick_config(), margin_visible=can_see_margin(user)))
    return out


@router.get("/estimates/{estimate_id}/summary", response_model=QuickSummary)
def summary(estimate_id: str, db: DbSession, user: CurrentUser) -> QuickSummary:
    estimate = get_owned(db, Estimate, estimate_id, user.org_id)
    project = get_owned(db, Project, estimate.project_id, user.org_id)
    return summary_for(db, estimate, project, quick_config(), margin_visible=can_see_margin(user))


@router.post("/estimates/{estimate_id}/check/confirm", response_model=QuickSummary)
def confirm_independent_check(estimate_id: str, db: DbSession, user: EditorUser) -> QuickSummary:
    """The user has looked at the gap the independent check found; export is then allowed."""
    estimate = get_owned(db, Estimate, estimate_id, user.org_id)
    project = get_owned(db, Project, estimate.project_id, user.org_id)
    confirm_check(db, user, estimate)
    return summary_for(db, estimate, project, quick_config(), margin_visible=can_see_margin(user))


@router.get("/estimates/{estimate_id}/options", response_model=list[PricedOption])
def open_options(estimate_id: str, db: DbSession, user: CurrentUser) -> list[PricedOption]:
    """Questions left open (not in the document, or "Not sure"), each with what the other
    answers would change in the likely price (nothing is saved)."""
    estimate = get_owned(db, Estimate, estimate_id, user.org_id)
    project = get_owned(db, Project, estimate.project_id, user.org_id)
    return priced_options(db, quick_config(), estimate, project)


class SecondOpinionState(BaseModel):
    ai_available: bool  # False: no AI key set, the page explains how to add one
    opinion: SecondOpinionOut | None


@router.get("/estimates/{estimate_id}/second-opinion", response_model=SecondOpinionState)
def get_second_opinion(estimate_id: str, db: DbSession, user: CurrentUser) -> SecondOpinionState:
    estimate = get_owned(db, Estimate, estimate_id, user.org_id)
    return SecondOpinionState(
        ai_available=ai_available(), opinion=second_opinion.latest(db, user, estimate)
    )


@router.post("/estimates/{estimate_id}/second-opinion", response_model=SecondOpinionState)
def ask_second_opinion(estimate_id: str, db: DbSession, user: EditorUser) -> SecondOpinionState:
    """The AI reviews the scope the price is built from (words only, never numbers)."""
    estimate = get_owned(db, Estimate, estimate_id, user.org_id)
    project = get_owned(db, Project, estimate.project_id, user.org_id)
    cfg = quick_config()
    if cfg.reality_check is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Second opinions are switched off.")
    plain = summarise(estimate, project, cfg, margin_visible=False)
    try:
        opinion = second_opinion.ask(db, user, cfg, estimate, plain)
    except LLMNotConfiguredError as exc:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Add an AI key in the server settings to use this."
        ) from exc
    except LLMRefusedError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc)) from exc
    return SecondOpinionState(ai_available=True, opinion=opinion)


@router.post("/quick-estimate/impact", response_model=list[QuestionImpact])
def impact(body: QuickRequest, db: DbSession, user: CurrentUser) -> list[QuestionImpact]:
    """Which questions change the price most for this form (nothing is saved)."""
    return question_impact(db, user, quick_config(), body)


class StandardBlockOut(BaseModel):
    key: str  # catalog block key (QuickRequest.not_included kind "standard")
    label: str
    hint: str


@router.post("/quick-estimate/standard-blocks", response_model=list[StandardBlockOut])
def standard(body: QuickRequest, _user: CurrentUser) -> list[StandardBlockOut]:
    """The standard building blocks this form brings at its size (nothing is saved or
    priced): the form lists them as included by default, and each can be unticked."""
    cfg = quick_config()
    out = []
    for key in standard_blocks(cfg, body):
        block = cfg.standard_blocks.get(key)
        out.append(
            StandardBlockOut(
                key=key, label=block.label if block else key, hint=block.hint if block else ""
            )
        )
    return out


class DescribeIn(BaseModel):
    text: str = Field(min_length=10, max_length=4000)  # a few lines about the software


@router.post("/quick-estimate/suggest", response_model=Suggestion)
def suggest(body: DescribeIn, _user: CurrentUser) -> Suggestion:
    """Features (and answers) suggested from the user's own description; nothing is saved
    or priced, the user ticks and confirms them on the form."""
    return suggest_features(quick_config(), body.text.strip())


@router.post("/quick-estimate/draft-stories", response_model=DraftOut)
def draft(body: DraftIn, _user: CurrentUser) -> DraftOut:
    """User stories for the ticked features, drafted by the AI for the user to edit and confirm
    (a project without a document). Nothing is saved or priced; the confirmed stories feed the
    story-size check only."""
    rules = quick_config().size_check
    if rules is None:
        return DraftOut(available=False, note="The story-size check is switched off.")
    return draft_stories(rules, body)

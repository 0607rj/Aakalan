"""Quick estimate: plain-language form -> confirmed project -> engine estimate -> plain summary.

The user's ticks and choices are the human review (rule 6): each ticked feature becomes a
confirmed requirement citing the quick-estimate form, and every component it adds is
confirmed by the same user. All numbers still come from the deterministic engine; the summary
only regroups and adds integer paise that the engine produced.
"""

import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from decimal import Decimal
from functools import lru_cache
from statistics import median, quantiles
from typing import Any, Literal

from fastapi import HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.config import get_settings
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
    PaymentMilestone,
    ProjectInfo,
    RequirementIn,
    SourceRef,
)
from app.services.engine.reference import Complexity, Size
from app.services.estimates import service as estimates
from app.services.estimates.reference_store import (
    catalog_for,
    get_parameter_set,
    get_rate_card,
    get_taxonomy,
)
from app.services.extraction.merge import project_extraction
from app.services.extraction.tender import FoundInventory
from app.services.quick.anchor import CheckLine, IndependentCheckOut, independent_check
from app.services.quick.config import (
    CostItemRule,
    Feature,
    LevelKey,
    Option,
    QuickConfig,
    SizeTier,
    quick_config,
)
from app.services.quick.reality import FeatureShare, RealityOut, SupportRule, reality_check
from app.services.research.service import PREFIX as RESEARCH_PREFIX
from app.services.research.service import resolve_features
from app.services.settings import (
    CompanySettings,
    apply_company_rates,
    apply_company_settings,
    company_settings,
)

FORM_DOCUMENT = "Quick estimate form"
SCOPE = "scope"  # requirement category of a chosen scope item
ONSITE_STAFF = "onsite_staff"
ONSITE_DAYS = "onsite_days"
ONSITE_PERIOD = "onsite_period"
FEW_BENCHMARKS = 5
ONE = Decimal(1)

TAX_BUCKET = "commercial.gst"
# Display grouping of taxonomy stages into plain-language parts of the total.
# Parts shown on their own, split out of their stage group: third-party and AI usage follow
# usage, not effort, so they are not mixed with development or support. "{years}" is filled in.
PART_SPLITS: dict[str, tuple[tuple[str, str, tuple[str, ...]], ...]] = {
    "build": (
        ("tools", "Developer tools and AI coding subscriptions", ("build.tools",)),
        ("translation", "Translating content into other languages", ("build.content_translation",)),
    ),
    "run": (
        ("ai_usage", "AI usage (chatbot and AI features) for {years}", ("run.ai_runtime",)),
        (
            "services",
            "Third-party services (SMS, email, maps, app stores) for {years}",
            ("run.third_party_services",),
        ),
    ),
}
PART_LABELS = {"run": "Running and supporting it for {years}"}
MARGIN_FALLBACK = "buffer"  # where margin is shown to users who may not see it
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
        "onsite_staff",  # people at the client's office during support (onsite_role)
        "onsite_days",  # only for these days in all (e.g. an event), not every support year
    }
)


class CustomFeature(BaseModel):
    """A feature outside the ready-made list: found in the document or added by the user."""

    name: str = Field(min_length=1, max_length=200)
    category: str
    size: Size
    found_index: int | None = None  # index into the document's other_features (for citations)
    # The catalog block that prices it (a published or researched block, services/research);
    # None = the generic block of its type. Set when the estimate is made, kept for re-runs.
    catalog_key: str | None = Field(default=None, max_length=100)


class QuickRequest(BaseModel):
    name: str = Field(min_length=1, max_length=300)
    project_type: str | None = None  # the first screen's answer; does not change the price
    country: str = "india"
    features: list[str] = []
    # How much of each ticked feature is built (basic / standard / advanced); unset = standard.
    feature_levels: dict[str, LevelKey] = {}
    custom_features: list[CustomFeature] = []
    choices: dict[str, str | int] = {}
    deadline_months: int | None = Field(default=None, ge=1, le=60)
    document_id: str | None = None  # a document uploaded via POST /documents
    overrides: dict[str, int | float] = {}
    # When the vendor is paid, as read from the document (shares add up to 1).
    payment_schedule: list[PaymentMilestone] | None = None
    # What else the features need (keys of the quick config's scope items); not chosen = not
    # priced. Items of a feature need that feature ticked.
    scope: list[str] = []
    # vendor: pricing our own bid; client: a department or company planning its budget
    # (tender estimate) - priced at market rates, with a bid check.
    mode: Literal["vendor", "client"] = "vendor"


class PlainPart(BaseModel):
    key: str
    label: str
    amount_paise: int  # most likely
    share_percent: int
    low_paise: int = 0  # optimistic and pessimistic values of the same lines
    high_paise: int = 0


class CostItem(BaseModel):
    """One plain line of "What's inside the price"."""

    group: str
    group_label: str
    key: str
    label: str
    amount_paise: int  # most likely; items sum to the planned cost
    low_paise: int = 0  # optimistic / pessimistic value of the same lines
    high_paise: int = 0
    person_days: int | None = None  # the work it pays for, when it is people's time
    person_days_low: int | None = None
    person_days_high: int | None = None
    traditional_paise: int | None = None  # the same item if the team used no AI tools


class TeamRole(BaseModel):
    """People of one role: full-time people on average over the period (the build, or one
    support year) and the work in person-months, from the engine's manpower rows."""

    role: str  # rate-card role key
    label: str
    people: Decimal  # average full-time people
    person_months: Decimal
    traditional_people: Decimal | None = None  # the same without AI tools
    traditional_person_months: Decimal | None = None


class HoursRow(BaseModel):
    """One role's hours over the build (the engine's person-days × hours per day)."""

    role: str
    label: str
    hours_with_ai: int
    hours_without_ai: int | None  # the same work without AI tools
    rupees_per_hour: Decimal  # the role's day rate in this estimate ÷ hours per day


class HoursSummary(BaseModel):
    """The build in hours: with the team's AI tools, without them, and the team's cost."""

    hours_per_day: int
    with_ai: int
    without_ai: int | None
    saved: int | None  # hours AI tools save, net of reviewing their work
    team_cost_paise: int  # the people's time over the build (engine labour lines, year 0)
    team_cost_without_ai_paise: int | None
    rows: list[HoursRow]


class MarketSource(BaseModel):
    label: str
    projects: int


class MarketOut(BaseModel):
    """What real projects were bought for, next to the should-cost estimate. basis
    "published_prices": the published prices of real projects the app gives the same size, in
    today's money with GST (P25 / median / P75), as published, not scaled to this estimate.
    "scaled_to_estimate" (parameter sets v14-v15 without benchmark data): P50 × a size band.
    Either way an observed price, not a check of the hours."""

    project_size: str  # Small / ... / Large
    projects: int  # real projects behind the figures (0 = between two sizes)
    low_paise: int  # middle half of real contracts
    mid_paise: int
    high_paise: int
    basis: Literal["published_prices", "scaled_to_estimate"] = "scaled_to_estimate"
    sizes: list[str] = []  # size groups the projects come from (neighbours added when few)
    sources: list[MarketSource] = []
    first_year: int | None = None  # award years of the projects
    last_year: int | None = None


class EraSensitivityOut(BaseModel):
    """Building blocks whose effort data has unknown AI use get no AI saving in the price. This
    is the same scope if that data predates AI tools (the team's AI savings applied to it):
    shown beside the price, never taken off it (engine run, `era_sensitivity`)."""

    low_paise: int  # the lower P10 of the two runs
    high_paise: int  # the estimate's own P90
    pre_ai_likely_paise: int  # most likely price if the data predates AI tools
    unknown_components: int
    components: int
    note: str


class FeatureCost(BaseModel):
    """Building one feature: the team's work on its building blocks (most likely), with the
    team's AI tools and without them. Launch, running, management and tax are not included."""

    label: str
    level: str | None  # Basic / Standard / Advanced; None for the standard building blocks
    amount_paise: int
    traditional_paise: int | None


class ScopeCost(BaseModel):
    """A chosen scope item and the building cost of the blocks only it asked for (most likely,
    split evenly when two items need the same new block). 0 = already in the project (a
    feature's or a standard block), so nothing was added."""

    key: str
    label: str  # "group: item"
    amount_paise: int
    note: str  # what is and is not priced
    partly_priced: bool = False  # part of the work is not priced (no evidence)


class SimilarProject(BaseModel):
    """A real project with a published price, close to this one."""

    title: str
    client: str
    client_type: str  # government / private / small_business
    size: str | None
    year: int
    low_paise: int  # in today's money (the published price, or the low end of its band)
    high_paise: int
    source_url: str
    match_percent: int


class BidCheck(BaseModel):
    """For a client planning a tender: the fair budget and where bids stop looking realistic."""

    fair_low_paise: int
    fair_high_paise: int
    too_low_below_paise: int  # bids under this are probably unrealistic: ask for justification
    too_high_above_paise: int  # bids over this are probably overpriced
    note: str


class ResearchSource(BaseModel):
    label: str  # the publisher's own wording, or the catalog block an analysis used
    url: str | None = None


class ResearchedFeature(BaseModel):
    """A feature priced by a block researched for it (services/research): from published hours
    found on the web and checked on the page ("web"), or from the AI's analysis of it as catalog
    blocks ("analysis"). Low confidence either way."""

    name: str
    method: Literal["web", "analysis"]
    section: str | None
    summary: str  # how its hours were found, in plain words
    sources: list[ResearchSource]


class ClientPays(BaseModel):
    """A cost the client pays providers directly; not part of the price."""

    key: str
    label: str
    first_year_paise: int | None  # amounts in the estimate currency, when they can be sized
    total_paise: int | None  # over the support years (plus any one-off purchase)
    first_year_low_paise: int | None = None
    first_year_high_paise: int | None = None
    total_low_paise: int | None = None
    total_high_paise: int | None = None
    note: str | None  # e.g. a per-payment fee that depends on the client's sales


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
    country: str
    currency: str  # all *_paise amounts are minor units of this currency (paise / cents)
    planned_paise: int
    risk_allowance_paise: int | None
    likely_without_tax_paise: int | None = None  # the likely price without GST
    build_only_paise: int  # building only: before support, margin, buffer and tax
    build_only_low_paise: int = 0
    build_only_high_paise: int = 0
    build_months: str
    support_years: int
    parts: list[PlainPart]
    biggest_uncertainty: str | None
    features: list[str]
    scope: list[str] = []  # scope items priced ("group: item"), see QuickRequest.scope
    scope_items: list[ScopeCost] = []  # each chosen item with what it added
    indicative: bool
    accuracy_note: str | None  # how this pricing performed on real published contracts
    traditional_paise: int | None  # same scope priced without AI tools (most likely)
    traditional_build_only_paise: int | None
    ai_saving_percent: int | None  # how much cheaper the AI-era price is
    client_pays: list[ClientPays] = []  # paid directly by the client, not in the price
    client_pays_first_year_paise: int = 0  # sum of the sized client-paid items, first year
    cost_items: list[CostItem] = []  # what's inside the price, item by item (sums to planned)
    similar_projects: list[SimilarProject] = []  # real projects close to this one
    feature_costs: list[FeatureCost] = []  # building cost of each feature, with and without AI
    team: list[TeamRole] = []  # people needed to build it, by role
    team_people: Decimal | None = None  # all roles together, average over the build
    traditional_build_months: str | None = None  # time to build without AI tools
    support_team: list[TeamRole] = []  # people per year after launch (year 1)
    hours: HoursSummary | None = None  # the build in hours, with and without AI tools
    should_cost: bool = False  # priced from effort, not tuned to market prices
    market: MarketOut | None = None  # real contracts of this size, for comparison
    era_sensitivity: EraSensitivityOut | None = None  # if the unknown-era data predates AI
    not_sure: list[str] = []  # questions answered "Not sure" (they widen the range)
    project_size: str | None = None  # Small / ... / Large, from what is built
    size_points: int | None = None
    mode: str = "vendor"  # vendor / client
    bid_check: BidCheck | None = None  # client mode only
    researched: list[ResearchedFeature] = []  # features priced by researched blocks
    reality: RealityOut | None = None  # "does this price look real?" checks
    # no support term chosen: the price holds one year of support, quoted as a yearly price
    support_term_open: bool = False
    # a second estimate counted from the document (uploads only); None for the form
    independent_check: IndependentCheckOut | None = None


def _default(cfg: QuickConfig, req: QuickRequest, key: str) -> str | int:
    """The question's default, or the one that follows another answer (default_by)."""
    question = cfg.questions[key]
    for other, by_value in question.default_by.items():
        answer = req.choices.get(other, cfg.questions[other].default)
        if str(answer) in by_value:
            return by_value[str(answer)]
    return question.default


def _choice(cfg: QuickConfig, req: QuickRequest, key: str) -> Any:
    question = cfg.questions[key]
    value = req.choices.get(key, _default(cfg, req, key))
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
    return f' Document says: "{found["evidence"][0]["quote"]}"'


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
class PlannedComponent:
    key: str
    size: Size
    complexity: Complexity
    requirements: list[str]
    label: str | None = None
    hard_problem: bool = False  # a feature the document's hard problems belong to


@dataclass
class QuickPlan:
    """Everything a quick estimate creates, before it touches the database. The same plan is
    persisted for a real estimate and converted in memory for "what if" pricing."""

    requirements: dict[str, PlannedRequirement] = field(default_factory=dict)
    components: list[PlannedComponent] = field(default_factory=list)
    answers: dict[str, tuple[Any, list[str]]] = field(default_factory=dict)
    size_points: int = 0
    project_size: str = ""
    clarity: int = 3  # requirement clarity (1-5); lower with "Not sure" answers
    levels: dict[str, str] = field(default_factory=dict)  # feature key -> level
    unsure: list[str] = field(default_factory=list)  # questions answered "Not sure"
    scope: list[str] = field(default_factory=list)  # scope items priced, in order
    # after an upload: questions the document does not answer, priced at the usual answer
    assumed: list[str] = field(default_factory=list)


def _unprocessable(message: str) -> HTTPException:
    return HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, message)


def plan_quick(
    cfg: QuickConfig,
    req: QuickRequest,
    extraction: dict[str, Any] | None,
    filename: str,
    *,
    project_size: str | None = None,
) -> QuickPlan:
    """The project a quick request describes. The price follows what is built: each feature's
    level sets its components' size and complexity and adds points; the total points set the
    project size (standard building blocks, launch defaults and the size factor). `project_size`
    pins the size instead (back-testing against projects whose size is known)."""
    unknown = set(req.choices) - set(cfg.questions)
    if unknown:
        raise _unprocessable(f"Unknown questions: {sorted(unknown)}")
    if req.project_type is not None and req.project_type not in {t.key for t in cfg.project_types}:
        raise _unprocessable(f"Unknown kind of software {req.project_type!r}")
    bad_overrides = set(req.overrides) - OVERRIDABLE
    if bad_overrides:
        raise _unprocessable(f"Unknown values: {sorted(bad_overrides)}")
    options = {key: _choice(cfg, req, key) for key in cfg.questions}
    try:
        added = added_features(options)
        features = [cfg.feature(k) for k in dict.fromkeys([*req.features, *added])]
    except ValueError as exc:
        raise _unprocessable(str(exc)) from exc
    if not features and not req.custom_features:
        raise _unprocessable("Tick or add at least one feature.")
    stray = set(req.feature_levels) - {f.key for f in features}
    if stray:
        raise _unprocessable(f"Levels given for features not ticked: {sorted(stray)}")
    try:
        chosen_scope = [cfg.scope_item(k) for k in dict.fromkeys(req.scope)]
    except ValueError as exc:
        raise _unprocessable(str(exc)) from exc
    # in the config's order, so the order they were ticked never changes component ids (and
    # with them the simulation's draws)
    rank = {i.key: n for n, (_, i) in enumerate((g, i) for g in cfg.scope for i in g.items)}
    chosen_scope.sort(key=lambda gi: rank[gi[1].key])
    ticked = {f.key for f in features}
    stray_scope = [
        i.key for g, i in chosen_scope if g.feature is not None and g.feature not in ticked
    ]
    if stray_scope:
        raise _unprocessable(f"Scope given for features not ticked: {stray_scope}")
    if len(req.custom_features) > cfg.max_custom_features:
        raise _unprocessable(f"At most {cfg.max_custom_features} extra features.")
    bad_types = {c.category for c in req.custom_features} - set(cfg.custom_feature_types)
    if bad_types:
        raise _unprocessable(f"Unknown feature types: {sorted(bad_types)}")
    country = cfg.countries.get(req.country)
    if country is None:
        raise _unprocessable(f"Unknown country {req.country!r}")
    if not country.enabled:
        raise _unprocessable(f"{country.label} is switched off for now.")
    hosting = options["hosting"].answers.get("hosting_provider")
    if hosting not in country.hosting_options:
        raise _unprocessable(f"{options['hosting'].label} is not available for {country.label}")
    default_level = next(
        (o.feature_level for o in options.values() if o.feature_level is not None),
        cfg.sizing.default_level,
    )
    levels: dict[str, LevelKey] = {
        f.key: req.feature_levels.get(f.key) or added.get(f.key) or default_level for f in features
    }
    custom_levels = [cfg.sizing.custom_size_level[c.size] for c in req.custom_features]
    points = sum(cfg.sizing.levels[levels[f.key]].points for f in features if f.counts_for_size)
    points += sum(cfg.sizing.levels[lv].points for lv in custom_levels)
    tier = cfg.sizing.tier_for(project_size) if project_size else cfg.sizing.tier(points)
    extraction = extraction or {}
    found_features = {f["key"]: f for f in extraction.get("features", [])}
    found_choices: dict[str, Any] = extraction.get("choices", {})
    found_numbers: dict[str, Any] = extraction.get("numbers", {})

    unsure = [key for key, o in options.items() if o.unsure]
    assumed = (
        _assumed(cfg, req, options, {f.key for f in features}, found_choices, found_numbers)
        if extraction
        else []
    )
    plan = QuickPlan(
        size_points=points,
        project_size=tier.project_size,
        clarity=_clarity(cfg, len(unsure), len(assumed)),
        unsure=unsure,
        levels=dict(levels),
        assumed=assumed,
    )

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

    standard = _standard_components(tier, options)
    component_reqs: dict[str, list[str]] = {k: [] for k in standard}
    component_level: dict[str, LevelKey] = {}
    for f in features:
        for key in f.components:
            component_reqs.setdefault(key, []).append(feature_req[f.key])
            component_level[key] = _larger(cfg, component_level.get(key), levels[f.key])
    # Scope items: each adds catalog blocks at its level. A block already in the project is
    # not added again (the larger level wins); a standard block keeps at least its project size.
    found_scope = {s["key"]: s for s in extraction.get("scope", [])}
    scope_level: dict[str, LevelKey] = {}  # standard blocks a scope item asks more of
    scope_label: dict[str, str] = {}  # blocks only scope items asked for -> first item's label
    # a general block (the custom-feature types') stands for the item's own system, so two
    # items needing one (an API and an e-signature service) are two blocks, not one
    generic = {t.component for t in cfg.custom_feature_types.values()}
    own_blocks: list[PlannedComponent] = []
    for group, item in chosen_scope:
        found = found_scope.get(item.key)
        refs = _evidence_refs(found, filename) or [
            {"clause_ref": f"Scope: {item.label}", "document": FORM_DOCUMENT}
        ]
        code = requirement(f"{group.label}: {item.label}.{_quote(found)}", SCOPE, refs)
        for key, wanted in item.adds.items():
            if key in generic:
                lv = cfg.sizing.levels[wanted]
                own_blocks.append(
                    PlannedComponent(key, lv.component_size, lv.complexity, [code], item.label)
                )
                continue
            if key in standard:
                scope_level[key] = _larger(cfg, scope_level.get(key), wanted)
            elif key not in component_reqs:
                scope_label[key] = item.label
            if key not in standard:
                component_level[key] = _larger(cfg, component_level.get(key), wanted)
            component_reqs.setdefault(key, []).append(code)
        plan.scope.append(item.key)
    complexity = {k: c for o in options.values() for k, c in o.component_complexity.items()}
    for key, reqs in component_reqs.items():
        if key in standard:  # a standard building block: sized by the project
            cx = complexity.get(key, Complexity.MEDIUM)  # e.g. a design that is ready
            size = tier.base_size
            if key in scope_level:
                size = _bigger(size, cfg.sizing.levels[scope_level[key]].component_size)
            plan.components.append(PlannedComponent(key, size, cx, reqs))
        else:
            level = cfg.sizing.levels[component_level[key]]
            plan.components.append(
                PlannedComponent(
                    key, level.component_size, level.complexity, reqs, scope_label.get(key)
                )
            )
    plan.components.extend(own_blocks)
    # the document's hard problems (independent check reading) widen their features' range
    inventory = extraction.get("inventory") or {}
    hard = {h.get("feature") for h in inventory.get("hard_problems", []) if h.get("feature")}
    hard_keys = {k for f in features if f.key in hard for k in f.components}
    for c in plan.components:
        c.hard_problem = c.key in hard_keys

    found_others: list[dict[str, Any]] = extraction.get("other_features", [])
    for custom in req.custom_features:
        found = None
        if custom.found_index is not None and 0 <= custom.found_index < len(found_others):
            found = found_others[custom.found_index]
        refs = _evidence_refs(found, filename) or [
            {"clause_ref": f"Added by user: {custom.name}", "document": FORM_DOCUMENT}
        ]
        detail = f" {found['description']}" if found and found.get("description") else ""
        code = requirement(f"{custom.name}.{detail}{_quote(found)}", "functional", refs)
        component = custom.catalog_key or cfg.custom_feature_types[custom.category].component
        level = cfg.sizing.levels[cfg.sizing.custom_size_level[custom.size]]
        plan.components.append(
            PlannedComponent(component, custom.size, level.complexity, [code], custom.name)
        )

    def cited(found: dict[str, Any] | None, label: str) -> list[str]:
        """Requirement keys proving a value, when the value the user kept came from the tender."""
        refs = _evidence_refs(found, filename)
        return [requirement(f"{label}.{_quote(found)}", "NFR", refs)] if refs else []

    for k, v in cfg.base_answers.items():
        plan.answers[k] = (v, [])
    plan.answers["project_size"] = (tier.project_size, [])
    if project_size is None:  # the size factor follows the feature points (parameter sets v13+)
        plan.answers["size_points"] = (points, [])
    for k, v in tier.answers.items():
        plan.answers[k] = (v, [])
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
    onsite_days = overrides.pop(ONSITE_DAYS, None)  # only with onsite_staff
    if onsite_days is None and req.choices.get(ONSITE_PERIOD) == "event" and cfg.onsite_event_days:
        onsite_days = str(cfg.onsite_event_days.days)  # an event, no days stated: the default
    for k, v in overrides.items():
        found = found_numbers.get(k)
        kept = found is not None and found["value"] == v
        reqs = cited(found, k.replace("_", " ").capitalize()) if kept else []
        if k == ONSITE_STAFF:
            if cfg.onsite_role is None:
                raise _unprocessable("Staff at the client's office cannot be priced.")
            limit = {"days": onsite_days} if onsite_days else {}
            if limit:
                days_found = found_numbers.get(ONSITE_DAYS)
                if days_found is not None and days_found["value"] == onsite_days:
                    reqs = [*reqs, *cited(days_found, "Onsite days")]
            staff = [{"role": cfg.onsite_role, "count": v, **limit}] if v > 0 else []
            plan.answers["onsite_resources"] = (staff, reqs)
        else:
            plan.answers[k] = (v, reqs)
    if req.payment_schedule is not None:
        if sum((m.percent for m in req.payment_schedule), Decimal(0)) != 1:
            raise _unprocessable("Payment shares must add up to 100%.")
        terms = extraction.get("payment_terms")
        reqs = cited(terms, "Payment terms") if terms else []
        schedule = [m.model_dump(mode="json") for m in req.payment_schedule]
        plan.answers["payment_schedule"] = (schedule, reqs)
    return plan


def added_features(options: dict[str, Any]) -> dict[str, LevelKey | None]:
    """Features the answers add (a mobile app, connecting other software, old data), each with
    its level (None = the default level)."""
    out: dict[str, LevelKey | None] = {}
    for option in options.values():
        out.update(option.add_features)
    return out


def request_features(cfg: QuickConfig, req: QuickRequest) -> list[str]:
    """Ticked features plus those the answers add."""
    try:
        options = {key: _choice(cfg, req, key) for key in cfg.questions}
    except HTTPException:
        return list(req.features)
    return list(dict.fromkeys([*req.features, *added_features(options)]))


def _clarity(cfg: QuickConfig, unsure: int, assumed: int = 0) -> int:
    """requirement clarity, lowered one step per `answers_per_step` "Not sure" answers, and
    one step per `assumed_per_step` answers a document left open (at most assumed_max_steps)."""
    rules = cfg.not_sure
    if rules is None or (unsure == 0 and assumed == 0):
        return cfg.requirement_clarity
    steps = -(-unsure // rules.answers_per_step)  # ceil
    if rules.assumed_per_step is not None and assumed:
        steps += min(rules.assumed_max_steps, -(-assumed // rules.assumed_per_step))
    return max(rules.min_clarity, cfg.requirement_clarity - steps)


def _assumed(
    cfg: QuickConfig,
    req: QuickRequest,
    options: dict[str, Option],
    features: set[str],
    found_choices: dict[str, Any],
    found_numbers: dict[str, Any],
) -> list[str]:
    """After an upload: questions that apply, the document does not answer (no choice, no
    number that answers them, no stated support term) and that are priced at their usual
    answer. "Not sure" answers are counted on their own."""
    custom_types = {c.category for c in req.custom_features}
    out = []
    for key, q in cfg.questions.items():
        if q.group == "hidden" or key in found_choices or options[key].unsure:
            continue
        limited = q.only_with_features or q.only_with_custom_types
        if limited and not (
            features & set(q.only_with_features) or custom_types & set(q.only_with_custom_types)
        ):
            continue
        if any(str(_choice(cfg, req, k).value) in map(str, v) for k, v in q.hide_when.items()):
            continue
        if q.answered_by_number and q.answered_by_number in {*req.overrides, *found_numbers}:
            continue
        if key == SUPPORT_YEARS and "om_years" in {*req.overrides, *found_numbers}:
            continue
        if str(options[key].value) == str(_default(cfg, req, key)):
            out.append(key)
    return out


def _standard_components(tier: SizeTier, options: dict[str, Any]) -> list[str]:
    """The project size's building blocks plus those the answers add (e.g. load testing for
    many users, fixing audit findings when an audit is asked for), in order, without repeats."""
    keys = [*tier.base_components]
    for option in options.values():
        keys += option.extra_components
    return list(dict.fromkeys(keys))


SIZE_RANK = {Size.S: 0, Size.M: 1, Size.L: 2}


def _bigger(a: Size, b: Size) -> Size:
    return a if SIZE_RANK[a] >= SIZE_RANK[b] else b


def _larger(cfg: QuickConfig, a: LevelKey | None, b: LevelKey) -> LevelKey:
    """A component shared by two features is built to the larger of their levels."""
    if a is None:
        return b
    return a if cfg.sizing.levels[a].points >= cfg.sizing.levels[b].points else b


def feature_level_options(cfg: QuickConfig, feature: Feature) -> dict[LevelKey, str]:
    """What each level means for a feature: its own words, else the generic hint."""
    return {k: feature.levels.get(k, lv.hint) for k, lv in cfg.sizing.levels.items()}


def _document_context(
    db: Session, user: User, document_id: str | None
) -> tuple[Document | None, dict[str, Any] | None, str]:
    if not document_id:
        return None, None, FORM_DOCUMENT
    doc = get_owned(db, Document, document_id, user.org_id)
    project = get_owned(db, Project, doc.project_id, user.org_id)
    merged = project_extraction(db, project).extraction  # all files of the project
    return doc, merged.model_dump(mode="json") if merged else None, doc.filename


AI_USE = "ai_use"


def with_company_defaults(db: Session, user: User, req: QuickRequest) -> QuickRequest:
    """An unanswered AI-use question follows the company's saved AI level (Settings)."""
    level = company_settings(db, user.org_id).team_ai_maturity
    if level is None or AI_USE in req.choices:
        return req
    return req.model_copy(update={"choices": {**req.choices, AI_USE: level}})


def with_catalog_blocks(
    db: Session, user: User, cfg: QuickConfig, req: QuickRequest, research: bool
) -> QuickRequest:
    """Each custom feature priced by its catalog block when there is one: a close published
    or researched block, else (research=True, with an AI key) a block researched now and
    saved for the organisation; otherwise the generic block of its type."""
    keys = {c.key for c in catalog_for(db, user.org_id).components}
    given = [c.catalog_key for c in req.custom_features if c.catalog_key]
    unknown = [k for k in given if k not in keys]
    if unknown:
        raise _unprocessable(f"Unknown catalog blocks: {unknown}")
    open_ = [c for c in req.custom_features if not c.catalog_key]
    if not open_:
        return req
    research_cfg = cfg if research else cfg.model_copy(update={"research": None})
    found = resolve_features(db, user, research_cfg, [(c.name, c.category) for c in open_])
    by_id = {id(c): k for c, k in zip(open_, found, strict=True)}
    return req.model_copy(
        update={
            "custom_features": [
                c.model_copy(update={"catalog_key": by_id.get(id(c)) or c.catalog_key})
                for c in req.custom_features
            ]
        }
    )


def create_quick_estimate(db: Session, user: User, cfg: QuickConfig, req: QuickRequest) -> Estimate:
    req = with_company_defaults(db, user, req)
    req = with_catalog_blocks(db, user, cfg, req, research=True)
    doc, extraction, filename = _document_context(db, user, req.document_id)
    plan = plan_quick(cfg, req, extraction, filename)
    now = datetime.now(UTC)
    if doc is not None:
        project = get_owned(db, Project, doc.project_id, user.org_id)
        _reset(db, project)
        project.name = req.name
        project.country = req.country
        project.quick_request = req.model_dump(mode="json", exclude={"document_id"})
        project.mode = BUYER_MODE if req.mode == "client" else VENDOR_MODE
    else:
        project = Project(
            org_id=user.org_id,
            name=req.name,
            country=req.country,
            buyer_type="govt",
            domain="quick_estimate",
            description="Created with the quick estimate form.",
            created_by=user.id,
            quick_request=req.model_dump(mode="json", exclude={"document_id"}),
            mode=BUYER_MODE if req.mode == "client" else VENDOR_MODE,
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
            clarity_score=plan.clarity,
            status="confirmed",
            source_refs=planned.refs,
            confirmed_by=user.id,
            confirmed_at=now,
        )
        db.add(row)
        db.flush()
        ids[code] = row.id
    for c in plan.components:
        db.add(
            ComponentInstance(
                org_id=user.org_id,
                project_id=project.id,
                catalog_key=c.key,
                label=c.label,
                size=c.size.value,
                complexity=c.complexity.value,
                quantity=1,
                driver_values={"hard_problem": True} if c.hard_problem else {},
                requirement_ids=[ids[r] for r in c.requirements],
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
    inp = estimates.build_input(db, project, as_of=now.date(), seed=request_seed(req, doc))
    return estimates.create_estimate(db, project, user, inp)


def request_seed(req: QuickRequest, doc: Document | None) -> int:
    """The simulation seed follows what was asked (answers, features, the file's contents), not
    the upload or the estimate's name: the same file and answers give the same range."""
    asked = req.model_dump(mode="json", exclude={"document_id", "name"})
    key = json.dumps([asked, doc.sha256 if doc else None], sort_keys=True)
    return int(hashlib.sha256(key.encode("utf-8")).hexdigest(), 16) % (1 << estimates.SEED_BITS)


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
                clarity_score=plan.clarity,
                source_refs=[SourceRef.model_validate(ref) for ref in r.refs],
            )
            for code, r in plan.requirements.items()
        ],
        components=[
            ComponentInstanceIn(
                id=f"C{i:03d}",
                catalog_key=c.key,
                label=c.label,
                size=c.size,
                complexity=c.complexity,
                requirement_ids=c.requirements,
                hard_problem=c.hard_problem,
            )
            for i, c in enumerate(plan.components, start=1)
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
    req = with_company_defaults(db, user, req)
    req = with_catalog_blocks(db, user, cfg, req, research=False)
    _, extraction, filename = _document_context(db, user, req.document_id)
    today = datetime.now(UTC).date()
    # a client planning a budget sees market prices, not this company's own settings
    settings = CompanySettings() if req.mode == "client" else company_settings(db, user.org_id)
    reference = {
        "taxonomy": get_taxonomy(db),
        "catalog": catalog_for(db, user.org_id),
        "rate_card": apply_company_rates(get_rate_card(db, None, today, req.country), settings),
        "parameters": apply_company_settings(
            get_parameter_set(db, None, today, req.country), settings
        ),
        "clarity": cfg.requirement_clarity,
    }
    out = []
    for key, question in cfg.questions.items():
        if question.group in ("hidden", "document"):  # never asked on the form
            continue
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


class OptionChange(BaseModel):
    value: str | int
    label: str
    change_paise: (
        int | None
    )  # likely price with this answer minus the estimate's (None: infeasible)


class PricedOption(BaseModel):
    """A question left open (not in the document, or answered "Not sure"): priced at its usual
    answer, with what each other answer would change. Fast fixed-seed re-pricing (quick config
    `impact`) of the estimate's own snapshot, so the changes use its pinned rates."""

    key: str
    question: str
    priced_as: str  # the answer in the price
    why: Literal["not_in_document", "not_sure"]
    low_change_paise: int | None  # smallest and largest change over the other answers
    high_change_paise: int | None
    options: list[OptionChange]


def priced_options(
    db: Session, cfg: QuickConfig, estimate: Estimate, project: Project
) -> list[PricedOption]:
    """Every open question with the price change of each other answer, largest first."""
    if not project.quick_request:
        return []
    req = QuickRequest.model_validate(project.quick_request)
    merged = project_extraction(db, project)
    extraction = merged.extraction.model_dump(mode="json") if merged.extraction else None
    filename = merged.documents[0].filename if merged.documents else FORM_DOCUMENT
    snap = EstimateInput.model_validate(estimate.inputs_snapshot)
    reference = {
        "taxonomy": snap.taxonomy,
        "catalog": snap.catalog,
        "rate_card": snap.rate_card,
        "parameters": snap.parameters,
    }
    today = estimate.as_of_date

    def likely(r: QuickRequest) -> int | None:
        plan = plan_quick(cfg, r, extraction, filename)
        inp = plan_to_input(
            plan, req.name, reference, today, cfg.impact.seed, cfg.impact.monte_carlo_runs
        )
        totals = calculate(inp).totals
        return totals.p50_paise if totals else None

    base_plan = plan_quick(cfg, req, extraction, filename)
    base = likely(req)
    if base is None:
        return []
    open_keys: list[tuple[str, Literal["not_in_document", "not_sure"]]] = [
        (k, "not_in_document") for k in base_plan.assumed
    ]
    open_keys += [(k, "not_sure") for k in base_plan.unsure if k not in base_plan.assumed]
    out = []
    for key, why in open_keys:
        question = cfg.questions[key]
        current = _choice(cfg, req, key)
        changes = []
        for option in question.options:
            if option.unsure or option.value == current.value:
                continue
            variant = req.model_copy(update={"choices": {**req.choices, key: option.value}})
            try:
                price = likely(variant)
            except HTTPException:  # an answer this form cannot take (e.g. hosting by country)
                continue
            changes.append(
                OptionChange(
                    value=option.value,
                    label=option.label,
                    change_paise=None if price is None else price - base,
                )
            )
        known = [c.change_paise for c in changes if c.change_paise is not None]
        if not changes:
            continue
        out.append(
            PricedOption(
                key=key,
                question=question.label,
                priced_as=current.label,
                why=why,
                low_change_paise=min(known) if known else None,
                high_change_paise=max(known) if known else None,
                options=changes,
            )
        )
    out.sort(key=lambda o: -max((abs(c.change_paise or 0) for c in o.options), default=0))
    return out


def confirm_check(db: Session, user: User, estimate: Estimate) -> None:
    """A person has looked at the gap the independent check found; export is allowed."""
    estimate.check_confirmed_at = datetime.now(UTC)
    estimate.check_confirmed_by = user.id
    db.commit()


def summary_for(
    db: Session, estimate: Estimate, project: Project, cfg: QuickConfig, *, margin_visible: bool
) -> QuickSummary:
    """The summary with the independent check of the project's documents (when it has any)."""
    merged = project_extraction(db, project).extraction
    return summarise(
        estimate,
        project,
        cfg,
        margin_visible=margin_visible,
        document=merged is not None,
        inventory=merged.inventory if merged else None,
    )


def summarise(
    estimate: Estimate,
    project: Project,
    cfg: QuickConfig,
    *,
    margin_visible: bool = True,
    document: bool = False,
    inventory: FoundInventory | None = None,
) -> QuickSummary:
    """`document`: the project was priced from an uploaded document, so the independent check
    is made (from `inventory`, the document's count of what the system contains)."""
    result: dict[str, Any] = estimate.result
    stage_likely = {g["key"]: g["likely_paise"] for g in result["by_stage"]}
    stage_low = {g["key"]: g["low_paise"] for g in result["by_stage"]}
    stage_high = {g["key"]: g["high_paise"] for g in result["by_stage"]}
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
                low_paise=sum(stage_low.get(s, 0) for s in stages),
                high_paise=sum(stage_high.get(s, 0) for s in stages),
            )
        )
    years = _om_years(estimate)
    plural = "s" if years != 1 else ""
    parts = _split_parts(parts, result["by_bucket"], planned, f"{years} year{plural}")
    traditional: dict[str, Any] = result.get("traditional") or {}
    client_pays = _client_pays(result)
    drivers = result["top_drivers"]
    biggest = None
    if drivers:
        top = drivers[0]
        phrase = cfg.plain_drivers.get(top["bucket"], top["name"])
        biggest = f"The biggest unknown is {phrase}."
    infeasible = result.get("infeasibility")
    timeline = result["timeline"]
    summary = QuickSummary(
        project_id=project.id,
        estimate_id=estimate.id,
        name=project.name,
        created_at=estimate.created_at,
        feasible=estimate.feasible,
        message=infeasible["message"] if infeasible else None,
        low_paise=estimate.p10_paise,
        likely_paise=estimate.p50_paise,
        high_paise=estimate.p90_paise,
        country=estimate.inputs_snapshot["rate_card"].get("region", "india"),
        currency=estimate.inputs_snapshot["rate_card"].get("currency", "INR"),
        planned_paise=planned,
        risk_allowance_paise=(estimate.p50_paise - planned) if estimate.p50_paise else None,
        likely_without_tax_paise=_without_tax(result, estimate.p50_paise, planned),
        build_only_paise=sum(stage_likely.get(s, 0) for s in BUILD_ONLY_STAGES),
        build_only_low_paise=sum(stage_low.get(s, 0) for s in BUILD_ONLY_STAGES),
        build_only_high_paise=sum(stage_high.get(s, 0) for s in BUILD_ONLY_STAGES),
        build_months=str(timeline["delivery_duration_months"]),
        support_years=years,
        parts=parts,
        biggest_uncertainty=biggest,
        features=[
            r.text_normalised.split(". ", 1)[0].rstrip(".")
            for r in project.requirements
            if r.category == "functional"
        ],
        scope=[
            r.text_normalised.split(". ", 1)[0].rstrip(".")
            for r in project.requirements
            if r.category == SCOPE
        ],
        indicative=estimate.calibration_status == "uncalibrated",
        accuracy_note=_accuracy_note(estimate),
        traditional_paise=traditional.get("p50_paise"),
        traditional_build_only_paise=traditional.get("build_only_paise"),
        ai_saving_percent=_saving(estimate.p50_paise, traditional.get("p50_paise")),
        client_pays=client_pays,
        client_pays_first_year_paise=sum(c.first_year_paise or 0 for c in client_pays),
        cost_items=cost_items(cfg, estimate, years, margin_visible),
        similar_projects=similar_projects(cfg, estimate, project) if cfg.show_market_prices else [],
        feature_costs=(costs := feature_costs(cfg, estimate, project)),
        scope_items=scope_costs(cfg, project, costs),
        team=(build_team := team_by_role(cfg, result, 0)),
        team_people=sum((r.people for r in build_team), Decimal(0)) if build_team else None,
        traditional_build_months=traditional.get("delivery_months"),
        support_team=team_by_role(cfg, result, 1),
        hours=hours_summary(cfg, estimate),
        should_cost=bool(_calibration_of(estimate).get("should_cost")),
        market=(_published_prices(cfg, estimate, project) or _market(cfg, result))
        if cfg.show_market_prices
        else None,
        era_sensitivity=_era_sensitivity(result),
        not_sure=_not_sure(cfg, project),
        project_size=_size_label(cfg, estimate),
        size_points=_size_points(cfg, project),
        mode="client" if project.mode == BUYER_MODE else "vendor",
        bid_check=_bid_check(cfg, estimate) if project.mode == BUYER_MODE else None,
        researched=researched_features(estimate),
        support_term_open=_support_term_open(cfg, project),
    )
    emd = next(
        (
            a["value"]
            for a in estimate.inputs_snapshot.get("answers", [])
            if a["key"] == "emd_paise"
        ),
        None,
    )
    emd_paise = emd if isinstance(emd, int) else None
    if document and cfg.independent_check is not None and estimate.feasible:
        summary.independent_check = independent_check(
            cfg.independent_check,
            inventory,
            priced_pd=Decimal(str(timeline["build_effort_pd"])),
            pd_per_month=Decimal(
                str(estimate.inputs_snapshot["parameters"]["calendar"]["pd_per_month"])
            ),
            project_size=summary_size(estimate),
            top_lines=_top_build_lines(estimate),
            price_without_tax_paise=summary.likely_without_tax_paise or summary.likely_paise,
            emd_paise=emd_paise,
            emd_rules=cfg.reality_check,
            confirmed_at=estimate.check_confirmed_at,
        )
    return with_reality(cfg, summary, emd_paise, result.get("sanity_checks", []))


TOP_LINES = 3
BUILD_STAGES = ("pre_build", "build")


def _top_build_lines(estimate: Estimate) -> list[CheckLine]:
    """The largest building lines (most likely), where a gap with the check usually sits."""
    build = [
        ln for ln in estimate.lines if ln.stage in BUILD_STAGES and not ln.derived and ln.year == 0
    ]
    build.sort(key=lambda ln: -ln.likely_paise)
    return [CheckLine(label=ln.label, amount_paise=ln.likely_paise) for ln in build[:TOP_LINES]]


def summary_size(estimate: Estimate) -> str | None:
    """The project size the estimate was priced at (quick answers), e.g. "medium"."""
    for a in estimate.inputs_snapshot.get("answers", []):
        if a["key"] == "project_size":
            return str(a["value"]) if a["value"] else None
    return None


SUPPORT_YEARS = "support_years"
PER_YEAR = "per_year"


def _support_term_open(cfg: QuickConfig, project: Project) -> bool:
    """No support term chosen or read from the document: one year is priced as a yearly rate."""
    req = project.quick_request or {}
    if "om_years" in (req.get("overrides") or {}) or SUPPORT_YEARS not in cfg.questions:
        return False
    chosen = (req.get("choices") or {}).get(SUPPORT_YEARS, cfg.questions[SUPPORT_YEARS].default)
    return str(chosen) == PER_YEAR


def _without_tax(result: dict[str, Any], likely: int | None, planned: int) -> int | None:
    """The likely price without GST: GST is a fixed share of every line, so the likely price
    loses the same share as the planned cost."""
    if not likely or not planned:
        return None
    tax: int = sum(b["likely_paise"] for b in result["by_bucket"] if b["key"] == TAX_BUCKET)
    return round(Decimal(likely) * (planned - tax) / planned)


def with_reality(
    cfg: QuickConfig,
    summary: QuickSummary,
    emd_paise: int | None = None,
    sanity_checks: list[dict[str, Any]] | None = None,
) -> QuickSummary:
    """The summary with its "does this price look real?" checks (when configured). The engine's
    support rule of thumb is explained with the independent check's direction: support looks
    low beside a build that is itself priced high."""
    rules = cfg.reality_check
    if rules is None or not summary.feasible:
        return summary
    shares = [
        FeatureShare(
            label=f.label, amount_paise=f.amount_paise, standard=f.label == STANDARD_BLOCKS
        )
        for f in summary.feature_costs
    ]
    reality = reality_check(
        rules,
        shares,
        summary.build_only_paise,
        {p.key: p.amount_paise for p in summary.parts},
        summary.support_years,
        summary.team_people,
        [r.name for r in summary.researched],
        len(summary.not_sure),
        price_paise=summary.likely_without_tax_paise or summary.likely_paise,
        emd_paise=emd_paise,
        support_rule=_support_rule(sanity_checks or []),
        build_looks=_build_looks(summary.independent_check),
    )
    return summary.model_copy(update={"reality": reality})


SUPPORT_RULE = "maintenance_rule_of_thumb"


def _support_rule(sanity_checks: list[dict[str, Any]]) -> SupportRule | None:
    """The engine's year-1 support share and the rule of thumb it was compared with."""
    for c in sanity_checks:
        if c.get("key") != SUPPORT_RULE:
            continue
        message = str(c.get("message", ""))
        m = SUPPORT_SHARES.search(message)
        below = m is not None and Decimal(m.group(1)) < Decimal(m.group(2))
        return SupportRule(ok=c.get("status") == "ok", message=message, below=below)
    return None


# engine/core.py: "Year-1 maintenance is 14.2% of build cost; the industry rule of thumb is 15–25%."
SUPPORT_SHARES = re.compile(r"is ([\d.]+)% of build cost; .*? is (\d+)\D")


def _build_looks(check: IndependentCheckOut | None) -> Literal["high", "low"] | None:
    """Whether the independent check finds the build high or low (ratio, else its band)."""
    if check is None or not check.available:
        return None
    if check.direction is not None:
        return check.direction
    if check.band is not None and check.band.position != "inside":
        return "high" if check.band.position == "above" else "low"
    return None


HOSTING_BUCKETS = ("run.hosting", "run.backups", "run.dr", "go_live.infrastructure_procurement")
HOSTING_LABEL = "Hosting (servers, database, storage, backups)"
HOSTING_NOTE = (
    "Sized at public cloud prices; less if the client uses its own or a government data centre."
)
YEAR_SUFFIX = re.compile(r" \(year \d+\)$")
SAME_ITEM = {"waf_requests": "waf_base"}  # shown as one "web firewall" item
PLAIN_LABELS = {"llm_api": "AI chatbot usage", "gpu": "AI chatbot servers (GPU)"}
NO_SUPPORT = "No support after launch (handed over to the client)"


def researched_features(estimate: Estimate) -> list[ResearchedFeature]:
    """Researched blocks this estimate used, from its own snapshot (never today's data)."""
    snap = estimate.inputs_snapshot
    used = {c["catalog_key"] for c in snap.get("components", [])}
    out = []
    for c in snap.get("catalog", {}).get("components", []):
        if c["key"] not in used or not c["key"].startswith(RESEARCH_PREFIX):
            continue
        evidence = c.get("evidence") or []
        web = any(e.get("url") for e in evidence)
        out.append(
            ResearchedFeature(
                name=c["name"],
                method="web" if web else "analysis",
                section=c.get("section"),
                summary=c.get("source", ""),
                sources=[ResearchSource(label=e["citation"], url=e.get("url")) for e in evidence],
            )
        )
    return out


def _client_pays(result: dict[str, Any]) -> list[ClientPays]:
    """Group the client-paid lines (hosting as one item, each service on its own) and add
    the per-transaction notes."""
    groups: dict[str, dict[str, Any]] = {}
    for ln in result.get("client_paid", []):
        hosting = ln["bucket"] in HOSTING_BUCKETS
        key = "hosting" if hosting else ln["line_key"].split("/")[1]
        key = SAME_ITEM.get(key, key)
        label = (
            HOSTING_LABEL if hosting else PLAIN_LABELS.get(key) or YEAR_SUFFIX.sub("", ln["label"])
        )
        g = groups.setdefault(
            key, {"label": label, "first": [0, 0, 0], "total": [0, 0, 0]}
        )  # [low, likely, high]
        points = (ln["low_paise"], ln["likely_paise"], ln["high_paise"])
        g["total"] = [a + b for a, b in zip(g["total"], points, strict=True)]
        if ln["year"] == 1:
            g["first"] = [a + b for a, b in zip(g["first"], points, strict=True)]
    items = [
        ClientPays(
            key=k,
            label=g["label"],
            first_year_paise=g["first"][1],
            total_paise=g["total"][1],
            first_year_low_paise=g["first"][0],
            first_year_high_paise=g["first"][2],
            total_low_paise=g["total"][0],
            total_high_paise=g["total"][2],
            note=HOSTING_NOTE if k == "hosting" else None,
        )
        for k, g in groups.items()
    ]
    items += [
        ClientPays(
            key=n["key"], label=n["label"], first_year_paise=None, total_paise=None, note=n["text"]
        )
        for n in result.get("client_paid_notes", [])
    ]
    return items


VENDOR_MODE, BUYER_MODE = "vendor", "buyer"


def _bid_check(cfg: QuickConfig, estimate: Estimate) -> BidCheck | None:
    """Fair budget = the estimate's P10-P90; bids below / above the configured shares of those
    ends are flagged (abnormally low bids risk failure; high ones overpay)."""
    rules = cfg.client_mode
    if rules is None or estimate.p10_paise is None or estimate.p90_paise is None:
        return None
    return BidCheck(
        fair_low_paise=estimate.p10_paise,
        fair_high_paise=estimate.p90_paise,
        too_low_below_paise=int(Decimal(estimate.p10_paise) * rules.too_low_share_of_low),
        too_high_above_paise=int(Decimal(estimate.p90_paise) * rules.too_high_share_of_high),
        note=rules.note,
    )


MIN_PUBLISHED = 1000  # a band's lower edge at or below this (minor units) means "under ..."
SIZE_ORDER = ("small", "small_medium", "medium", "medium_large", "large")


@lru_cache
def _benchmarks(country: str) -> list[Any]:
    from app.services.calibration.backtest import load_benchmarks  # avoid an import cycle

    path = get_settings().seeds_dir / "benchmarks" / f"{country}.yaml"
    return [b for b in load_benchmarks(path).projects if b.use] if path.exists() else []


def similar_projects(
    cfg: QuickConfig, estimate: Estimate, project: Project
) -> list[SimilarProject]:
    """The real projects closest to this estimate (features, size, build type), with their
    published prices brought to today's money."""
    rules = cfg.similar_projects
    if rules is None or not project.quick_request:
        return []
    snapshot = estimate.inputs_snapshot
    answers = {a["key"]: a["value"] for a in snapshot.get("answers", [])}
    try:
        features = set(request_features(cfg, QuickRequest.model_validate(project.quick_request)))
    except ValueError:  # saved with an older form
        features = set(project.quick_request.get("features", []))
    size = answers.get("project_size")
    build = answers.get("build_type", "custom")
    escalation = Decimal(str(snapshot["parameters"]["escalation"]["labour"]))
    this_year = estimate.created_at.year
    scored = []
    for b in _benchmarks(project.country):
        m = b.model
        shared = features | set(m.features)
        jaccard = Decimal(len(features & set(m.features))) / len(shared) if shared else Decimal(0)
        score = rules.weight_features * jaccard
        if size and m.size == size:
            score += rules.weight_size
        elif _neighbours(size, m.size):
            score += rules.weight_neighbour_size
        score += rules.weight_build_type if (m.build_type or "custom") == build else 0
        if score >= rules.min_score:
            scored.append((score, b))
    scored.sort(key=lambda sb: (-sb[0], sb[1].id))
    out = []
    for score, b in scored[: rules.count]:
        low = _today(b.value_minor, b.award_year, this_year, escalation)
        high = _today(b.value_high_minor or b.value_minor, b.award_year, this_year, escalation)
        out.append(
            SimilarProject(
                title=b.title,
                client=b.buyer,
                client_type=b.model.buyer,
                size=b.model.size,
                year=b.award_year,
                low_paise=low if b.value_minor > MIN_PUBLISHED else 0,  # 0 = 'up to'
                high_paise=high,
                source_url=b.source_url,
                match_percent=round(100 * score),
            )
        )
    return out


@lru_cache(maxsize=4)
def _benchmark_sizes(country: str) -> dict[str, str]:
    """The size the app gives each benchmark's scope (from its feature points), by id."""
    from app.services.calibration.backtest import derived_size  # avoid an import cycle

    cfg = quick_config()
    sizes = {}
    for b in _benchmarks(country):
        try:
            sizes[b.id] = derived_size(cfg, b, country)
        except HTTPException:  # scope too thin to model
            continue
    return sizes


def _published_prices(cfg: QuickConfig, estimate: Estimate, project: Project) -> MarketOut | None:
    """Published prices of real projects the app gives this estimate's size (neighbouring sizes
    added below `min_projects`): today's money (× (1 + escalation)^years), GST added where a
    price excludes it, a price band at its middle; P25 / median / P75. Never scaled to the
    estimate."""
    rules = cfg.market_comparison
    snapshot = estimate.inputs_snapshot
    answers = {a["key"]: a["value"] for a in snapshot.get("answers", [])}
    size = answers.get("project_size")
    if rules is None or size not in SIZE_ORDER:
        return None
    benchmarks = {b.id: b for b in _benchmarks(project.country)}
    sizes = _benchmark_sizes(project.country)
    groups = [size]
    chosen = [benchmarks[i] for i, s in sizes.items() if s == size]
    if len(chosen) < rules.min_projects:
        groups = [s for s in SIZE_ORDER if s == size or _neighbours(size, s)]
        chosen = [benchmarks[i] for i, s in sizes.items() if s in groups]
    if len(chosen) < 2:
        return None
    escalation = Decimal(str(snapshot["parameters"]["escalation"]["labour"]))
    gst = Decimal(str(snapshot["parameters"]["commercial"]["gst_percent"]))
    this_year = estimate.created_at.year
    prices = []
    sources: dict[str, int] = {}
    for b in chosen:
        low = b.value_minor if b.value_minor > MIN_PUBLISHED else 0
        value = Decimal(low + b.value_high_minor) / 2 if b.value_high_minor else b.value_minor
        if b.value_includes_tax is False:
            value *= 1 + gst
        prices.append(_today(int(value), b.award_year, this_year, escalation))
        host = b.source_url.split("/")[2].removeprefix("www.")
        label = rules.sources.get(host, rules.other_source)
        sources[label] = sources.get(label, 0) + 1
    q = quantiles(prices, n=4, method="inclusive")
    labels = [cfg.sizing.tier_for(g).label for g in groups]
    return MarketOut(
        project_size=cfg.sizing.tier_for(size).label,
        projects=len(chosen),
        low_paise=round(q[0]),
        mid_paise=round(median(prices)),
        high_paise=round(q[2]),
        basis="published_prices",
        sizes=labels,
        sources=[
            MarketSource(label=k, projects=v)
            for k, v in sorted(sources.items(), key=lambda kv: -kv[1])
        ],
        first_year=min(b.award_year for b in chosen),
        last_year=max(b.award_year for b in chosen),
    )


def _neighbours(a: str | None, b: str | None) -> bool:
    """True for adjacent project sizes (e.g. small and small_medium)."""
    if a not in SIZE_ORDER or b not in SIZE_ORDER:
        return False
    return abs(SIZE_ORDER.index(a) - SIZE_ORDER.index(b)) == 1


def _today(minor: int, year: int, this_year: int, escalation: Decimal) -> int:
    """A published price in today's money: × (1 + escalation)^(years since)."""
    return int(Decimal(minor) * (1 + escalation) ** max(0, this_year - year))


OTHER_ITEM = "Other"
BUILD_ONLY_STAGES = ("pre_build", "build", "go_live")


def cost_items(
    cfg: QuickConfig, estimate: Estimate, years: int, margin_visible: bool
) -> list[CostItem]:
    """Every cost line placed in exactly one plain item (config order; first match wins), with
    the person-days behind people's time. Items sum to the planned cost. Margin is merged into
    the risk buffer for users who may not see it."""
    period = f"{years} year{'s' if years != 1 else ''}"
    groups = {g.key: g.label.format(years=period) for g in cfg.cost_item_groups}
    rules = list(cfg.cost_items)
    traditional = _traditional_lines(estimate)
    # (group, key) -> [label, likely, pd, people, low, high, pd_low, pd_high, traditional]
    acc: dict[tuple[str, str], list[Any]] = {}

    def rule_for(line_key: str, bucket: str) -> CostItemRule | None:
        for rule in rules:
            if any(line_key.startswith(p) for p in rule.line_prefixes) or bucket in rule.buckets:
                return rule
        return None

    for ln in sorted(estimate.lines, key=lambda x: x.sort_order):
        rule = rule_for(ln.line_key, ln.bucket)
        if rule is not None and rule.margin and not margin_visible:
            rule = next((r for r in rules if r.key == MARGIN_FALLBACK), rule)
        if rule is None:
            group, key, label, people = ln.stage, "other", OTHER_ITEM, False
        else:
            group, key, label, people = rule.group, rule.key, rule.label, rule.people
            if rule.per_line:
                key = f"{rule.key}.{ln.line_key.split('/')[1]}"
                label = YEAR_SUFFIX.sub("", ln.label)
        item = acc.setdefault(
            (group, key), [label, 0, Decimal(0), people, 0, 0, Decimal(0), Decimal(0), 0]
        )
        if traditional is not None:
            item[8] += traditional.get(ln.line_key, 0)
        pd = sum((Decimal(str(v)) for v in ln.role_pd.values()), Decimal(0))
        item[1] += ln.likely_paise
        item[2] += pd
        item[4] += ln.low_paise
        item[5] += ln.high_paise
        if ln.likely_paise:  # the work moves with the money: same spread as the line
            item[6] += pd * ln.low_paise / ln.likely_paise
            item[7] += pd * ln.high_paise / ln.likely_paise
    order = {g.key: i for i, g in enumerate(cfg.cost_item_groups)}
    return [
        CostItem(
            group=group,
            group_label=groups.get(group, group),
            key=key,
            label=label,
            amount_paise=amount,
            low_paise=low,
            high_paise=high,
            person_days=round(pd) if people and pd else None,
            person_days_low=round(pd_low) if people and pd else None,
            person_days_high=round(pd_high) if people and pd else None,
            traditional_paise=trad if traditional is not None else None,
        )
        for (group, key), (label, amount, pd, people, low, high, pd_low, pd_high, trad) in sorted(
            acc.items(), key=lambda kv: order.get(kv[0][0], len(order))
        )
        if amount
    ]


def _traditional_lines(estimate: Estimate) -> dict[str, int] | None:
    """Each line's most-likely value without AI tools (estimates from this version on)."""
    traditional: dict[str, Any] = estimate.result.get("traditional") or {}
    lines: dict[str, int] | None = traditional.get("lines")
    return lines


PEOPLE_QUANTUM = Decimal("0.1")
RATE_QUANTUM = Decimal("0.01")


def _role_days(rows: list[dict[str, Any]]) -> dict[str, Decimal]:
    """role -> person-days over the build (year 0, every stage)."""
    out: dict[str, Decimal] = {}
    for r in rows:
        if r["year"] == 0:
            out[r["role"]] = out.get(r["role"], Decimal(0)) + Decimal(str(r["person_days"]))
    return out


def hours_summary(cfg: QuickConfig, estimate: Estimate) -> HoursSummary | None:
    """The build in hours: the engine's person-days by role × hours per day, the same without
    AI tools, each role's rate per hour (its day rate in this estimate's rate card ÷ hours per
    day), and the team's cost: the engine's labour lines over the build. Only regroups."""
    result: dict[str, Any] = estimate.result
    days = _role_days(result.get("manpower", []))
    if not days:
        return None
    traditional: dict[str, Any] = result.get("traditional") or {}
    old = _role_days(traditional["manpower"]) if "manpower" in traditional else None
    per_day = cfg.hours_per_person_day
    items = {
        i["key"]: Decimal(str(i["amount"]))
        for i in estimate.inputs_snapshot.get("rate_card", {}).get("items", [])
    }

    def hours(d: Decimal) -> int:
        return int((d * per_day).to_integral_value())

    rows = sorted(
        (
            HoursRow(
                role=role,
                label=cfg.role_labels.get(role, role.removeprefix("role.").replace("_", " ")),
                hours_with_ai=hours(d),
                hours_without_ai=hours(old.get(role, Decimal(0))) if old is not None else None,
                rupees_per_hour=(items.get(role, Decimal(0)) / per_day).quantize(RATE_QUANTUM),
            )
            for role, d in days.items()
            if hours(d) > 0 or (old is not None and hours(old.get(role, Decimal(0))) > 0)
        ),
        key=lambda r: -r.hours_with_ai,
    )
    with_ai = sum(r.hours_with_ai for r in rows)
    without_ai = sum(r.hours_without_ai or 0 for r in rows) if old is not None else None
    labour = {ln.line_key for ln in estimate.lines if ln.year == 0 and ln.role_pd}
    team_cost = sum(ln.likely_paise for ln in estimate.lines if ln.line_key in labour)
    old_lines: dict[str, int] | None = traditional.get("lines")
    return HoursSummary(
        hours_per_day=per_day,
        with_ai=with_ai,
        without_ai=without_ai,
        saved=(without_ai - with_ai) if without_ai is not None else None,
        team_cost_paise=team_cost,
        team_cost_without_ai_paise=sum(old_lines.get(k, 0) for k in labour)
        if old_lines is not None
        else None,
        rows=rows,
    )


def _people(rows: list[dict[str, Any]], year: int) -> dict[str, tuple[Decimal, Decimal]]:
    """role -> (average full-time people, person-months) in `year` (0 = the build).

    people = Σ_stage average_fte (each stage's FTE is over its own period: the delivery for
    pre-build / build / go-live, the programme for management, a year for support)."""
    acc: dict[str, tuple[Decimal, Decimal]] = {}
    for r in rows:
        if r["year"] != year:
            continue
        fte, pm = acc.get(r["role"], (Decimal(0), Decimal(0)))
        acc[r["role"]] = (
            fte + Decimal(str(r["average_fte"])),
            pm + Decimal(str(r["person_months"])),
        )
    return acc


def team_by_role(cfg: QuickConfig, result: dict[str, Any], year: int) -> list[TeamRole]:
    """People by role for the build (year 0) or one support year, most people first, with the
    same team without AI tools when the estimate has one. Only regroups engine output."""
    ours = _people(result.get("manpower", []), year)
    traditional: dict[str, Any] = result.get("traditional") or {}
    old = _people(traditional["manpower"], year) if "manpower" in traditional else None
    rows = [
        TeamRole(
            role=role,
            label=cfg.role_labels.get(role, role.removeprefix("role.").replace("_", " ")),
            people=fte.quantize(PEOPLE_QUANTUM),
            person_months=pm.quantize(PEOPLE_QUANTUM),
            traditional_people=old.get(role, (Decimal(0),) * 2)[0].quantize(PEOPLE_QUANTUM)
            if old is not None
            else None,
            traditional_person_months=old.get(role, (Decimal(0),) * 2)[1].quantize(PEOPLE_QUANTUM)
            if old is not None
            else None,
        )
        for role, (fte, pm) in ours.items()
        if pm.quantize(PEOPLE_QUANTUM) > 0  # hide roles with almost no work
    ]
    return sorted(rows, key=lambda r: (-r.people, r.label))


STANDARD_BLOCKS = "Standard building blocks (screens design, login and roles, testing, set-up)"


def feature_costs(cfg: QuickConfig, estimate: Estimate, project: Project) -> list[FeatureCost]:
    """The team's building cost per feature: each component line goes to the features that
    asked for it (split evenly when shared, remainder to the first); a block only scope items
    added goes to those items (e.g. "Sign-in and user accounts: Two-step sign-in (MFA)"); lines
    of components no feature asked for are the standard building blocks (also when a scope item
    made one bigger). Sums to the component lines."""
    snapshot = estimate.inputs_snapshot

    def labels_of(category: str) -> dict[str, str]:
        return {
            r["id"]: r["text"].split(". ", 1)[0].rstrip(".")
            for r in snapshot.get("requirements", [])
            if r["category"] == category
        }

    features, scope = labels_of("functional"), labels_of(SCOPE)
    owners = {}
    for c in snapshot.get("components", []):
        reqs = c.get("requirement_ids", [])
        owners[c["id"]] = [features[r] for r in reqs if r in features] or (
            [scope[r] for r in reqs if r in scope] if c.get("label") else []
        )
    traditional = _traditional_lines(estimate)
    acc: dict[str, list[int]] = {}  # label -> [with AI, without AI]
    for ln in sorted(estimate.lines, key=lambda x: x.sort_order):
        cid = ln.line_key.split("/", 1)[1] if "/" in ln.line_key else ""
        if cid not in owners:
            continue
        labels = owners[cid] or [STANDARD_BLOCKS]
        old = traditional.get(ln.line_key, 0) if traditional is not None else 0
        for i, label in enumerate(labels):
            item = acc.setdefault(label, [0, 0])
            item[0] += ln.likely_paise // len(labels) + (
                ln.likely_paise % len(labels) if i == 0 else 0
            )
            item[1] += old // len(labels) + (old % len(labels) if i == 0 else 0)
    plan = _replan(cfg, project)
    levels: dict[str, str] = plan.levels if plan else {}
    level_by_label = {
        f.label: cfg.sizing.levels[levels[f.key]].label  # type: ignore[index]
        for f in cfg.features
        if f.levels and f.key in levels
    }
    out = [
        FeatureCost(
            label=label,
            level=level_by_label.get(label) if label != STANDARD_BLOCKS else None,
            amount_paise=amount,
            traditional_paise=old if traditional is not None else None,
        )
        for label, (amount, old) in acc.items()
        if label != STANDARD_BLOCKS
    ]
    if STANDARD_BLOCKS in acc:
        amount, old = acc[STANDARD_BLOCKS]
        out.append(
            FeatureCost(
                label=STANDARD_BLOCKS,
                level=None,
                amount_paise=amount,
                traditional_paise=old if traditional is not None else None,
            )
        )
    return out


def scope_costs(cfg: QuickConfig, project: Project, costs: list[FeatureCost]) -> list[ScopeCost]:
    """The chosen scope items with the building cost of what each added (`feature_costs` rows
    of blocks only scope items asked for); an item whose blocks were already there adds 0."""
    try:
        keys = QuickRequest.model_validate(project.quick_request or {"name": "x"}).scope
    except ValueError:  # saved with an older form
        return []
    by_label = {c.label: c.amount_paise for c in costs}
    out = []
    for key in dict.fromkeys(keys):
        try:
            group, item = cfg.scope_item(key)
        except ValueError:  # an item no longer offered
            continue
        label = f"{group.label}: {item.label}"
        out.append(
            ScopeCost(
                key=key,
                label=label,
                amount_paise=by_label.get(label, 0),
                note=item.note,
                partly_priced=item.partly_priced,
            )
        )
    return out


def _not_sure(cfg: QuickConfig, project: Project) -> list[str]:
    """The questions answered "Not sure", in plain words."""
    choices: dict[str, Any] = (project.quick_request or {}).get("choices", {})
    out = []
    for key, value in choices.items():
        question = cfg.questions.get(key)
        if question is None:
            continue
        option = next((o for o in question.options if o.value == value), None)
        if option is not None and option.unsure:
            out.append(question.label)
    return out


def _size_label(cfg: QuickConfig, estimate: Estimate) -> str | None:
    answers = {a["key"]: a["value"] for a in estimate.inputs_snapshot.get("answers", [])}
    size = answers.get("project_size")
    try:
        return cfg.sizing.tier_for(str(size)).label if size else None
    except ValueError:
        return None


def _replan(cfg: QuickConfig, project: Project) -> QuickPlan | None:
    """The plan of a quick estimate's saved form (levels and points); None for other estimates
    and for forms saved with an older set of questions."""
    req = project.quick_request
    if not req:
        return None
    try:
        return plan_quick(cfg, QuickRequest.model_validate(req), None, FORM_DOCUMENT)
    except (HTTPException, ValueError):
        return None


def _size_points(cfg: QuickConfig, project: Project) -> int | None:
    """The feature points behind the project size (quick estimates only)."""
    plan = _replan(cfg, project)
    return plan.size_points if plan else None


def _split_parts(
    parts: list[PlainPart], by_bucket: list[dict[str, Any]], planned: int, years: str
) -> list[PlainPart]:
    """Move third-party, tool and AI-usage buckets out of their stage group into parts of their
    own (only when non-zero), so development and support show only labour."""
    amounts = {g["key"]: g["likely_paise"] for g in by_bucket}
    lows = {g["key"]: g["low_paise"] for g in by_bucket}
    highs = {g["key"]: g["high_paise"] for g in by_bucket}

    def share(amount: int) -> int:
        return round(100 * amount / planned) if planned else 0

    out: list[PlainPart] = []
    for part in parts:
        extra = []
        for key, label, buckets in PART_SPLITS.get(part.key, ()):
            amount = sum(amounts.get(b, 0) for b in buckets)
            if amount:
                extra.append(
                    PlainPart(
                        key=key,
                        label=label.format(years=years),
                        amount_paise=amount,
                        share_percent=share(amount),
                        low_paise=sum(lows.get(b, 0) for b in buckets),
                        high_paise=sum(highs.get(b, 0) for b in buckets),
                    )
                )
        rest = part.amount_paise - sum(p.amount_paise for p in extra)
        rest_low = part.low_paise - sum(p.low_paise for p in extra)
        rest_high = part.high_paise - sum(p.high_paise for p in extra)
        label = PART_LABELS.get(part.key, part.label).format(years=years)
        if part.key == "run" and years.startswith("0 "):
            label = NO_SUPPORT
        out.append(
            part.model_copy(
                update={
                    "label": label,
                    "amount_paise": rest,
                    "share_percent": share(rest),
                    "low_paise": rest_low,
                    "high_paise": rest_high,
                }
            )
        )
        out += extra
    return out


def _saving(ai_era: int | None, traditional: int | None) -> int | None:
    if not ai_era or not traditional or traditional <= 0:
        return None
    return round(100 * (traditional - ai_era) / traditional)


def _calibration_of(estimate: Estimate) -> dict[str, Any]:
    cal: dict[str, Any] = (estimate.inputs_snapshot.get("parameters") or {}).get(
        "calibration"
    ) or {}
    return cal


def _market(cfg: QuickConfig, result: dict[str, Any]) -> MarketOut | None:
    m = result.get("market")
    if not m:
        return None
    try:
        label = cfg.sizing.tier_for(m["project_size"]).label
    except ValueError:
        label = m["project_size"]
    return MarketOut(
        project_size=label,
        projects=m["projects"],
        low_paise=m["low_paise"],
        mid_paise=m["mid_paise"],
        high_paise=m["high_paise"],
    )


ERA_NOTE = (
    "{unknown} of {total} building blocks are priced from effort data that does not show "
    "whether AI tools were used, so no AI saving is taken off them. If that data predates AI "
    "tools, your team's AI tools would save more: the range then starts lower."
)


def _era_sensitivity(result: dict[str, Any]) -> EraSensitivityOut | None:
    s = result.get("era_sensitivity")
    if not s:
        return None
    return EraSensitivityOut(
        low_paise=s["range_low_paise"],
        high_paise=s["range_high_paise"],
        pre_ai_likely_paise=s["p50_paise"],
        unknown_components=s["unknown_components"],
        components=s["components"],
        note=ERA_NOTE.format(unknown=s["unknown_components"], total=s["components"]),
    )


SHOULD_COST_NOTE = (
    "Priced from the hours each feature takes (published effort data) and the rates, not "
    "from what vendors charged."
)
RANGE_NOTE = (
    " The range runs from about {below}% below to {above}% above the middle price: how much "
    "different teams' hours differ for the same scope (ISBSG; Anda et al. 2009) and the unknowns "
    "in each item. It has not yet been checked against what finished projects really cost."
)


def _should_cost_note(estimate: Estimate) -> str:
    """The note plus the estimate's own range, in % of P50 (from P10 and P90)."""
    p10, p50, p90 = estimate.p10_paise, estimate.p50_paise, estimate.p90_paise
    if not (p10 and p50 and p90):
        return SHOULD_COST_NOTE
    below = round(100 * (p50 - p10) / p50)
    above = round(100 * (p90 - p50) / p50)
    return SHOULD_COST_NOTE + RANGE_NOTE.format(below=below, above=above)


def _accuracy_note(estimate: Estimate) -> str | None:
    cal = _calibration_of(estimate)
    if cal.get("should_cost"):
        return _should_cost_note(estimate)
    n, err = cal.get("backtest_projects", 0), cal.get("median_abs_error_percent")
    if not n or err is None:
        return None
    answers = {a["key"]: a["value"] for a in estimate.inputs_snapshot.get("answers", [])}
    held, held_err = cal.get("holdout_projects", 0), cal.get("holdout_median_abs_error_percent")
    if held and held_err is not None:  # the honest figure: projects it was not tuned on
        return (
            f"Tested on {n} real projects with published prices. On {held} projects it had not "
            f"been tuned on, estimates were typically within ±{Decimal(str(held_err)):.0f}% of "
            "the price actually paid, so treat this as a guide and use your own judgement."
            + _size_note(cal, answers.get("project_size"))
        )
    return (
        f"Tested on {n} real project{'s' if n != 1 else ''} with published prices: estimates "
        f"were typically within ±{max(Decimal(str(err)), ONE):.0f}% of the price paid."
        + _size_note(cal, answers.get("project_size"))
        + (" Few contracts so far, so treat this as provisional." if n < FEW_BENCHMARKS else "")
    )


def _size_note(cal: dict[str, Any], size: str | None) -> str:
    """How projects of this size did in the back-test, e.g. ' For small projects, 5 of 8 ...'."""
    tested = cal.get("size_backtest", {}).get(size) if size else None
    if not tested or not size:
        return ""
    k, within = tested["projects"], tested["within_25_percent"]
    plain = size.replace("_", " to ")
    return f" For {plain} projects, {within} of {k} came within ±25%." + (
        f" {tested['note']}" if tested.get("note") else ""
    )


def _om_years(estimate: Estimate) -> int:
    for a in estimate.inputs_snapshot.get("answers", []):
        if a["key"] == "om_years":
            return int(a["value"])
    return int(estimate.inputs_snapshot["parameters"]["defaults"]["values"]["om_years"])

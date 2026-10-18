"""Quick-estimate configuration (`seeds/quick_estimate.yaml`): plain-language features and
questions that map to catalog components and questionnaire drivers. No prices live here."""

from decimal import Decimal
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.config import get_settings
from app.services.engine.reference import Complexity, Size


class Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class Feature(Frozen):
    key: str
    label: str
    hint: str
    components: list[str]
    sets: dict[str, Any] = {}
    counts_for_size: bool = True  # small add-ons do not make the standard blocks bigger
    # What Basic / Standard / Advanced mean for this feature (plain words; optional).
    levels: dict[str, str] = {}
    hidden: bool = False  # not in the tick list: a question's answer adds it (add_features)


LevelKey = Literal["basic", "standard", "advanced"]


class Option(Frozen):
    value: str | int
    label: str
    hint: str = ""
    answers: dict[str, Any]
    extra_components: list[str] = []  # standard building blocks this answer adds
    max_users: int | None = None  # scale question only; None = open-ended
    # Features this answer adds, at a level (None = the default level), e.g. a mobile app.
    add_features: dict[str, LevelKey | None] = {}
    feature_level: LevelKey | None = None  # default level of every feature (MVP / full)
    component_complexity: dict[str, Complexity] = {}  # e.g. a ready design: ui_ux_design low
    unsure: bool = False  # "Not sure": the usual answer, with a wider range


class Question(Frozen):
    label: str
    default: str | int
    options: list[Option]
    # main = one screen each; detail = the optional details screen; hidden = not asked
    group: Literal["main", "detail", "hidden"] = "main"
    # Ask only when one of these features or custom-feature types is chosen (empty = always).
    only_with_features: list[str] = []
    only_with_custom_types: list[str] = []
    # Hide when another question has one of these answers, e.g. {support_years: [0]}.
    hide_when: dict[str, list[str | int]] = {}
    # Default that follows another answer, e.g. {support_years: {"0": none}}.
    default_by: dict[str, dict[str, str | int]] = {}

    @model_validator(mode="after")
    def _default_exists(self) -> "Question":
        if self.default not in {o.value for o in self.options}:
            raise ValueError(f"default {self.default!r} is not an option")
        return self

    def option(self, value: str | int) -> Option:
        for o in self.options:
            if o.value == value:
                return o
        raise ValueError(f"{value!r} is not a valid choice")


class Keywords(Frozen):
    features: dict[str, list[str]]
    choices: dict[str, dict[str, list[str]]]
    # In documents of at least this many pages, a feature must be mentioned in this many
    # places to be ticked automatically (fewer: offered, not ticked).
    long_document_pages: int = Field(default=20, ge=1)
    min_mentions_long_document: int = Field(default=3, ge=1)


class Impact(Frozen):
    """Settings for ranking questions by price impact (fast, fixed-seed re-pricing)."""

    monte_carlo_runs: int = Field(ge=100)
    seed: int = Field(ge=0)


class Prebid(Frozen):
    vague_phrases: list[str]
    vague_query: str
    missing: dict[str, str]


ProjectSize = Literal["small", "small_medium", "medium", "medium_large", "large"]


class Level(Frozen):
    """How much of a feature is built: sets its components' size and complexity, and the
    points it adds to the project size."""

    label: str
    hint: str
    component_size: Size
    complexity: Complexity
    points: int = Field(ge=0)


class SizeTier(Frozen):
    """A project size, reached by the total feature points: sets the standard building blocks
    (and their size) and the launch-support defaults."""

    max_points: int | None  # None = open-ended
    project_size: ProjectSize
    label: str
    base_size: Size
    base_components: list[str]
    answers: dict[str, Any] = {}


class Sizing(Frozen):
    source: str
    default_level: LevelKey
    levels: dict[LevelKey, Level]
    custom_size_level: dict[Size, LevelKey]  # a custom feature's S/M/L as a level
    tiers: list[SizeTier]

    @model_validator(mode="after")
    def _open_tier(self) -> "Sizing":
        if not self.tiers or self.tiers[-1].max_points is not None:
            raise ValueError("sizing.tiers must end with an open tier")
        return self

    def tier(self, points: int) -> SizeTier:
        return next(t for t in self.tiers if t.max_points is None or points <= t.max_points)

    def tier_for(self, size: str) -> SizeTier:
        for t in self.tiers:
            if t.project_size == size:
                return t
        raise ValueError(f"unknown project size {size!r}")


class Country(Frozen):
    label: str
    currency: str
    hosting_options: list[str]
    enabled: bool = True  # switched off countries are hidden and cannot be priced


class CustomFeatureType(Frozen):
    label: str
    component: str


class CostItemGroup(Frozen):
    key: str
    label: str  # "{years}" is filled in with the support period


class CostItemRule(Frozen):
    """One plain cost item: the estimate lines whose bucket is in `buckets` (or whose line key
    starts with one of `line_prefixes`). `per_line` lists each distinct line on its own (e.g.
    each third-party service); `people` shows the person-days of work it pays for."""

    key: str
    group: str
    label: str
    buckets: list[str] = []
    line_prefixes: list[str] = []
    per_line: bool = False
    people: bool = False
    margin: bool = False  # hidden (merged into the buffer item) for users who may not see margin


class SimilarProjects(Frozen):
    """How "similar real projects" are matched: a weighted score of shared features (Jaccard),
    same or neighbouring size and same build type."""

    count: int = Field(ge=1)
    min_score: Decimal = Field(ge=0, le=1)
    weight_features: Decimal
    weight_size: Decimal
    weight_neighbour_size: Decimal
    weight_build_type: Decimal


class ClientMode(Frozen):
    """Bid check for clients planning a tender: shares of the fair range's ends."""

    source: str
    too_low_share_of_low: Decimal = Field(gt=0, le=1)
    too_high_share_of_high: Decimal = Field(ge=1)
    note: str


class NotSure(Frozen):
    """clarity = max(min_clarity, requirement_clarity − ceil(not-sure answers / per step))."""

    source: str
    answers_per_step: int = Field(ge=1)
    min_clarity: int = Field(ge=1, le=5)


class NotPricedTopic(Frozen):
    label: str
    words: list[str]


class PaymentPoint(Frozen):
    at_build_fraction: Decimal = Field(ge=0, le=1)
    offset_months: Decimal = Field(ge=0)


class PaymentPoints(Frozen):
    """When a payment the document describes falls (engine payment_schedule points)."""

    source: str
    on_order: PaymentPoint
    during_build: PaymentPoint
    go_live: PaymentPoint
    after_go_live: PaymentPoint


class ProjectType(Frozen):
    """A kind of software: which features to show first and to tick to start with."""

    key: str
    label: str
    hint: str
    features: list[str]  # shown first (empty = every feature)
    suggested: list[str] = []  # ticked to start with


class QuickConfig(Frozen):
    version: str
    source: str
    requirement_clarity: int = Field(ge=1, le=5)
    # Answers every quick estimate starts from (before sizes, questions and features).
    base_answers: dict[str, Any] = {}
    project_types: list[ProjectType] = []
    features: list[Feature]
    questions: dict[str, Question]
    plain_drivers: dict[str, str]
    keywords: Keywords
    impact: Impact
    prebid: Prebid
    custom_feature_types: dict[str, CustomFeatureType]
    countries: dict[str, Country]
    sizing: Sizing
    max_custom_features: int = Field(ge=1)
    # rate-card role key -> plain name, e.g. "role.qa_engineer": "Tester (QA)"
    role_labels: dict[str, str] = {}
    hours_per_person_day: int = Field(default=8, ge=1, le=24)  # to show work and rates in hours
    not_sure: NotSure | None = None
    not_priced_topics: dict[str, NotPricedTopic] = {}
    onsite_role: str | None = None  # rate-card role for staff at the client's office
    payment_points: PaymentPoints | None = None
    cost_item_groups: list[CostItemGroup] = []
    cost_items: list[CostItemRule] = []
    similar_projects: SimilarProjects | None = None
    client_mode: ClientMode | None = None

    def feature(self, key: str) -> Feature:
        for f in self.features:
            if f.key == key:
                return f
        raise ValueError(f"unknown feature {key!r}")


def load_quick_config(path: Path) -> QuickConfig:
    return QuickConfig.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))


@lru_cache
def quick_config() -> QuickConfig:
    return load_quick_config(get_settings().seeds_dir / "quick_estimate.yaml")

"""Quick-estimate configuration (`seeds/quick_estimate.yaml`): plain-language features and
questions that map to catalog components and questionnaire drivers. No prices live here."""

import re
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
    # an app on top of the website: its level follows the user stories of the features it
    # offers (from a document), not only its own (services/extraction/tender.py)
    sized_by_features: bool = False
    has_screens: bool = True  # False: back-office work an app never shows (e.g. data import)


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
    # "Not sure" that leaves these features out of the price and quotes them as an option
    # ("if required"), at these levels (None = the default level). Not counted as unclear:
    # what is left out does not widen the range. OPEN_QUESTIONS 147.
    left_out: dict[str, LevelKey | None] = {}
    # No longer offered on the form; kept so older estimates that chose it still price
    # (OPEN_QUESTIONS 173).
    retired: bool = False


class Question(Frozen):
    label: str
    default: str | int
    options: list[Option]
    # main = one screen each; detail = the optional details screen; hidden = not asked
    group: Literal["main", "detail", "document", "hidden"] = "main"
    # Ask only when one of these features or custom-feature types is chosen (empty = always).
    only_with_features: list[str] = []
    only_with_custom_types: list[str] = []
    # Hide when another question has one of these answers, e.g. {support_years: [0]}.
    hide_when: dict[str, list[str | int]] = {}
    # Default that follows another answer, e.g. {support_years: {"0": none}}.
    default_by: dict[str, dict[str, str | int]] = {}
    # File upload: "document" = the document decides what is built (read from it, else the
    # default), never asked; "ask" = asked when the document does not say.
    on_upload: Literal["ask", "document"] = "ask"
    # Not asked when this number is known (e.g. users_total): the answer is the option whose
    # max_users covers it.
    answered_by_number: str | None = None
    # A document whose reading lists this not-priced topic (with quotes) answers "yes" (e.g.
    # penalties): readings made before the question existed still answer it.
    from_not_priced: str | None = None
    # A document that does not mention it is not a gap: the usual answer applies without
    # lowering the requirement clarity (e.g. who provides the SSL certificate).
    silent_means_usual: bool = False
    # A decision the user must make on every estimate (no answer is pre-selected on the form,
    # and it is never "assumed"); `default` only serves requests that do not send it.
    must_choose: bool = False
    # What the answer means in numbers, shown with an assumed answer: a template filled with
    # the option's answers, e.g. "{users_total:,} users".
    detail: str | None = None
    # Only applies when this number is set (e.g. onsite_period needs onsite_staff).
    only_with_override: str | None = None

    @model_validator(mode="after")
    def _default_exists(self) -> "Question":
        values = {o.value for o in self.options}
        if self.default not in values:
            raise ValueError(f"default {self.default!r} is not an option")
        if self.from_not_priced and "yes" not in values:
            raise ValueError("a question answered by a not-priced topic needs a 'yes' option")
        return self

    def option(self, value: str | int) -> Option:
        for o in self.options:
            if o.value == value:
                return o
        raise ValueError(f"{value!r} is not a valid choice")


class Keywords(Frozen):
    features: dict[str, list[str]]
    # Everyday words for the same features, used only for a short description typed on the
    # form ("customers order food and track the rider"), never for tender documents.
    description_features: dict[str, list[str]] = {}
    choices: dict[str, dict[str, list[str]]]
    # In documents of at least this many pages, a feature must be mentioned in this many
    # places to be ticked automatically (fewer: offered, not ticked).
    long_document_pages: int = Field(default=20, ge=1)
    min_mentions_long_document: int = Field(default=3, ge=1)
    # A short description that rules a feature out ("no mobile app", "payments not needed"):
    # one of `exclusion_before` before the feature's words, or one of `exclusion_after` after
    # them, in one clause, with at most `exclusion_window_words` words between.
    exclusion_before: list[str] = []
    exclusion_after: list[str] = []
    exclusion_window_words: int = Field(default=1, ge=0)


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


class StorySizing(Frozen):
    """A feature found in a document takes its level from how many user stories the document
    asks for under it: up to basic_max stories = basic, up to standard_max = standard, more =
    advanced (services/extraction/tender.py). The reader lists stories; it never sizes.

    One advanced block covers up to advanced_max stories; a feature with more is several
    advanced modules: units = ceil(stories / advanced_max) (round 3, OPEN_QUESTIONS 152).
    Without advanced_max a feature is always one module (the earlier behaviour)."""

    source: str
    basic_max: int = Field(ge=1)
    standard_max: int = Field(ge=2)
    advanced_max: int | None = Field(default=None, ge=3)

    def level(self, stories: int) -> LevelKey:
        if stories <= self.basic_max:
            return "basic"
        return "standard" if stories <= self.standard_max else "advanced"

    def units(self, stories: int) -> int:
        """How many modules of its level the stories make: 1 up to advanced_max."""
        if self.advanced_max is None or stories <= self.advanced_max:
            return 1
        return -(-stories // self.advanced_max)  # ceil


class Sizing(Frozen):
    source: str
    default_level: LevelKey
    levels: dict[LevelKey, Level]
    custom_size_level: dict[Size, LevelKey]  # a custom feature's S/M/L as a level
    tiers: list[SizeTier]
    stories: StorySizing | None = None  # levels from a document's user stories
    # The most modules one feature or extra feature can be (units; 1 = no more than one).
    max_units: int = Field(default=1, ge=1)

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


class MarketComparison(Frozen):
    """Published prices of comparable real projects (seeds/benchmarks): projects the app gives
    the same size, with the neighbouring sizes added when there are too few."""

    min_projects: int = Field(ge=2)
    sources: dict[str, str]  # web address (host) -> plain description of that kind of price
    other_source: str


class ClientMode(Frozen):
    """Bid check for clients planning a tender: shares of the fair range's ends."""

    source: str
    too_low_share_of_low: Decimal = Field(gt=0, le=1)
    too_high_share_of_high: Decimal = Field(ge=1)
    note: str


class NotSure(Frozen):
    """clarity = max(min_clarity, requirement_clarity − ceil(not-sure answers / per step)
    − min(assumed_max_steps, ceil(assumed answers / assumed_per_step))). Assumed: after an
    upload, a question the document does not answer, priced at its usual answer."""

    source: str
    answers_per_step: int = Field(ge=1)
    min_clarity: int = Field(ge=1, le=5)
    assumed_per_step: int | None = Field(default=None, ge=1)  # None: assumed answers count 0
    assumed_max_steps: int = Field(default=0, ge=0)


SizeTierName = Literal["small", "medium", "large"]


class IndependentCheck(Frozen):
    """The independent check (services/quick/anchor.py): a build estimate from what the system
    must contain, counted from the document, compared with the priced build effort. Every
    figure is a placeholder prior with a source; the AI only lists named items with quotes."""

    source: str
    prompt: str  # prompts/<prompt>.md
    pd_per_entity: Decimal = Field(ge=0)
    pd_per_screen: Decimal = Field(ge=0)
    pd_per_role: Decimal = Field(ge=0)
    pd_per_integration: Decimal = Field(ge=0)
    pd_per_hard_problem: Decimal = Field(ge=0)
    screen_weight: dict[str, Decimal]  # single / list_detail_edit
    tenancy_pd: dict[str, Decimal]
    wrapper: Decimal = Field(gt=0)
    quality: dict[str, Decimal]
    ai_fit: dict[str, Decimal]
    clarity: dict[str, Decimal]
    ratio_low: Decimal = Field(gt=0, lt=1)
    ratio_high: Decimal = Field(gt=1)
    emd_block_factor: Decimal = Field(ge=1)
    size_tier: dict[str, SizeTierName]  # our project size -> the bands' size
    system_classes: dict[str, str]  # key -> plain label
    bands: dict[str, dict[SizeTierName, tuple[Decimal, Decimal]]]  # person-months [low, high]
    hard_problems: dict[str, str]  # key -> plain label

    @model_validator(mode="after")
    def _bands(self) -> "IndependentCheck":
        if set(self.bands) != set(self.system_classes):
            raise ValueError("independent_check.bands needs one entry per system class")
        for key, tiers in self.bands.items():
            if set(tiers) != {"small", "medium", "large"}:
                raise ValueError(f"independent_check.bands.{key} needs small, medium and large")
            if any(not 0 < low <= high for low, high in tiers.values()):
                raise ValueError(f"independent_check.bands.{key}: need 0 < low <= high")
        return self


class SizeCheck(Frozen):
    """The story-size check (services/quick/size_check.py, OPEN_QUESTIONS 163): the build sized
    from the document's user stories with a published function-point method, compared with our
    hours per feature. A check only; nothing here changes a price. `sources` gives the source
    of every figure."""

    sources: dict[str, str]  # figure -> where it comes from
    fp_per_story: Decimal = Field(gt=0)  # one user story = one elementary process
    fp_per_data_group: Decimal = Field(gt=0)
    data_groups_per_story: Decimal = Field(ge=0)
    hours_per_fp: dict[Literal["low", "likely", "high"], Decimal]  # delivery rate
    stages: list[str]  # our build stages compared (year 0)
    min_stories: int = Field(ge=1)  # fewer: the feature is too small to judge alone
    # build types that configure more than they build: the rate is for new code, so no verdict
    reuse_build_types: list[str] = []
    # user stories drafted by the AI when there is no document (services/quick/stories.py):
    # the user edits and confirms them; they feed this check only, never a level or a price
    draft_prompt: str  # prompts/<draft_prompt>.md
    draft_max_stories: int = Field(ge=1, le=50)  # per feature
    draft_max_chars: int = Field(ge=20, le=500)  # per story
    top_features: int = Field(ge=1)

    @model_validator(mode="after")
    def _check(self) -> "SizeCheck":
        figures = {"fp_per_story", "fp_per_data_group", "data_groups_per_story", "hours_per_fp"}
        if missing := figures - set(self.sources):
            raise ValueError(f"size_check.sources needs {sorted(missing)}")
        h = self.hours_per_fp
        if set(h) != {"low", "likely", "high"} or not 0 < h["low"] <= h["likely"] <= h["high"]:
            raise ValueError("size_check.hours_per_fp needs 0 < low <= likely <= high")
        return self


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


class ScopeItem(Frozen):
    """One piece of work a feature (or every project) may need beyond its baseline, e.g.
    two-step sign-in. It adds catalog building blocks at a level; a block that is already in
    the project (from a feature, the standard blocks or another item) is not added again: the
    larger level wins. Hours come from the catalog only."""

    key: str
    label: str
    adds: dict[str, LevelKey] = Field(min_length=1)  # catalog component key -> level
    note: str = ""  # what is and is not priced, in plain words (shown with the item)
    partly_priced: bool = False  # part of the work has no evidence and is not priced
    keywords: list[str] = []  # whole words / phrases that suggest it in a document (any case)


class ScopeGroup(Frozen):
    """Scope items for one feature (`feature`), or for every project (`feature: null`)."""

    key: str
    label: str
    feature: str | None = None
    items: list[ScopeItem] = Field(min_length=1)


class Research(Frozen):
    """Research for features the catalog lacks (services/research). Web: the AI only finds
    pages; the code opens each page, keeps a figure only if it is really there, and derives
    the hours from the kept figures (S / M / L = lowest / median / highest, x
    feature_level_factor / hours per day). Otherwise analysis: the AI composes the feature from
    catalog blocks at a level and the hours come from those blocks. The AI never gives a
    number. Every value here is a placeholder with a source."""

    source: str
    prompt: str  # prompts/<prompt>.md: find pages that state hours
    analyse_prompt: str  # prompts/<analyse_prompt>.md: compose the feature from catalog blocks
    web_search: bool = True  # look for published hours before the AI analysis
    min_verified_sources: int = Field(ge=1)  # fewer checked sources: not saved, custom type used
    max_sources: int = Field(ge=1, le=20)
    max_searches: int = Field(ge=1, le=20)
    max_per_estimate: int = Field(ge=0)  # features researched in one estimate (the rest: type)
    concurrency: int = Field(ge=1, le=10)
    feature_level_factor: Decimal = Field(gt=0, le=1)  # catalog v5 method (x 0.9)
    match_threshold: Decimal = Field(gt=0, le=1)  # word overlap to reuse an existing block
    retry_no_evidence_days: int = Field(ge=0)
    # Share each researched block with every organisation (services/research/library.py).
    share: bool = True
    fetch_timeout_seconds: int = Field(ge=1, le=120)
    fetch_max_bytes: int = Field(ge=10_000)
    quote_window_chars: int = Field(ge=20)  # a figure counts only near the feature's words
    min_hours: int = Field(ge=1)  # stated figures outside this range are not believed
    max_hours: int = Field(ge=1)


class RealityCheck(Frozen):
    """Common-sense checks on a finished estimate (services/quick/reality.py): does the price
    look like what is being built? Code only; nothing changes the price. Thresholds are
    reasoned placeholders with a source. `second_opinion_prompt`: the optional AI review
    (prompts/<name>.md), which names concerns but never gives a number."""

    source: str
    setup_share_max: Decimal = Field(gt=0, le=1)  # standard blocks' share of building
    feature_share_max: Decimal = Field(gt=0, le=1)  # one feature's share of the features
    feature_share_min_features: int = Field(ge=2)  # only with at least this many features
    run_per_year_max_of_build: Decimal = Field(gt=0)  # a year of running vs building
    max_average_team: Decimal = Field(gt=0)  # people on average during the build
    researched_share_max: Decimal = Field(gt=0, le=1)  # low-confidence researched features
    not_sure_max: int = Field(ge=0)  # "Not sure" answers before the range is called wide
    second_opinion_prompt: str
    second_opinion_max_flags: int = Field(ge=1, le=20)
    # EMD (bid security) is a share of the buyer's estimated value: the price is checked
    # against value = EMD ÷ share, and flagged when more than emd_band_factor outside it
    emd_share_min: Decimal | None = Field(default=None, gt=0, le=1)
    emd_share_max: Decimal | None = Field(default=None, gt=0, le=1)
    emd_band_factor: Decimal | None = Field(default=None, ge=1)  # 1: anywhere outside the range


class OnsiteEventDays(Frozen):
    days: Decimal = Field(gt=0)
    source: str


class IncludedItem(Frozen):
    key: str
    label: str  # what the reader is told is already in every price


class StandardBlock(Frozen):
    """A standard building block in plain words, shown on the form as included by default."""

    label: str
    hint: str = ""


class AlwaysIncluded(Frozen):
    """Work every estimate already prices (base blocks, run costs). A requirement that is only
    a part of one of these is not priced again as an extra (services/extraction/tender.py)."""

    source: str
    items: list[IncludedItem]


class ClientProvidedItem(Frozen):
    """Something the client may provide, and the answer that says so."""

    words: list[str]  # any one names the item in the sentence
    question: str
    value: str


class ClientProvided(Frozen):
    """A sentence saying the client provides an item (hosting, the web address, the SSL
    certificate) answers that item's question, citing the sentence. A sentence counts when it
    has one `give` phrase, one `by_client` word, an item word and no `by_vendor` phrase, and is
    at most `max_sentence_chars` long (long run-on text from lists is skipped). Whole words,
    any case. Found in code on the stored page text, so earlier readings get it too."""

    source: str
    give: list[str]
    by_client: list[str]
    by_vendor: list[str]
    max_sentence_chars: int = Field(ge=20)
    items: list[ClientProvidedItem]
    # The client by its own name (OPEN_QUESTIONS 157): "hosted on RailTel's cloud", "provisioned
    # by RailTel". A capitalised name before 's + one of `own_words`, or after one of `by_name`,
    # counts as a `by_client` word unless it is a vendor or a cloud brand (`not_client`).
    own_words: list[str] = []
    by_name: list[str] = []
    not_client: list[str] = []


class SupportTerms(Frozen):
    """Support hours and support staff a document states, found in code on the page text
    (OPEN_QUESTIONS 157). A sentence about the bidding portal's own helpdesk (`ignore`) never
    counts. Support hours: a `round_the_clock` phrase answers round the clock, staffed in shifts
    when the sentence says shifts or a roster (`staffed`, OPEN_QUESTIONS 162), else on call
    (uptime and availability wording included); without one, an `office_hours`
    phrase in a sentence about support answers office hours; else an SLA response faster than
    `fast_response_hours` (in a sentence about support) answers on call. Support staff: a stated
    number of `staff_words` in a sentence about support (`support_words`) with a `dedicated`
    word and no `onsite` word (people at the client's office are onsite_staff). When the hours
    are round the clock and another support sentence says office hours, the two are listed as a
    pre-bid query (`conflict_query`), not resolved silently."""

    source: str
    ignore: list[str]
    round_the_clock: list[str]
    staffed: list[str]
    office_hours: list[str]
    fast_response_hours: int = Field(ge=1)
    support_words: list[str]
    staff_words: list[str]
    dedicated: list[str]
    onsite: list[str]
    max_staff: int = Field(ge=1)
    max_sentence_chars: int = Field(ge=20)
    values: dict[Literal["office", "on_call", "always"], str]  # support_hours option values
    conflict_query: str


class StaffingQueries(Frozen):
    """Pre-bid query texts the staff rules raise; {role}, {count}, {place}, {page}, {note} and
    the price-table row's {table_role}, {table_count}, {table_place}, {table_page} are filled in."""

    table_conflict: str
    call_off: str
    call_off_hours: str
    place_not_stated: str
    quantity_unclear: str


class Staffing(Frozen):
    """Staff, support hours, helpdesk and chatbot level from the reading's staff lines, in code
    (services/extraction/staffing.py, OPEN_QUESTIONS 162)."""

    source: str
    helpdesk_words: list[str]
    queries: StaffingQueries
    # onsite staff whose name says they do the engine's own work (OPEN_QUESTIONS 166): whole
    # words or phrases, any case; management is checked first
    management_words: list[str] = []  # the O&M project manager
    upkeep_words: list[str] = []  # bug fixes, patches, upgrades, small changes


class CmsBuiltIn(Frozen):
    """What a CMS already has (OPEN_QUESTIONS 154). On a build of one of `build_types`, these
    features, and the extra features whose names say they are the CMS's own parts (editor,
    templates, versions, SEO ...), are set up rather than built: priced at most at `level`,
    one module each. A tender read story by story otherwise counts every built-in capability
    of the product as work to build."""

    source: str
    build_types: list[str]
    features: list[str]
    level: LevelKey
    extra_words: list[str]  # whole words in an extra feature's name, any case
    note: str  # added to each such requirement, so the quote says why it costs little

    def is_cms_part(self, name: str) -> bool:
        text = name.lower()
        return any(re.search(rf"\b{re.escape(w.lower())}\b", text) for w in self.extra_words)


class BacktestNote(Frozen):
    """The latest production-path back-test in plain words (OPEN_QUESTIONS 161), shown at the end
    of every estimate's accuracy note. Rewritten after each production-path back-test."""

    source: str
    text: str


class QuickConfig(Frozen):
    version: str
    source: str
    requirement_clarity: int = Field(ge=1, le=5)
    show_market_prices: bool = True  # show published contract prices beside the estimate
    # how the pricing did in the latest production-path back-test, added to the accuracy note
    backtest_note: BacktestNote | None = None
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
    # rate-card role for dedicated support staff a document states (offsite or not said)
    support_role: str | None = None
    support_terms: SupportTerms | None = None  # support hours and staff read in code
    staffing: Staffing | None = None  # staff lines priced in code (OPEN_QUESTIONS 162)
    onsite_event_days: OnsiteEventDays | None = None  # onsite only for an event, no days given
    payment_points: PaymentPoints | None = None
    cost_item_groups: list[CostItemGroup] = []
    cost_items: list[CostItemRule] = []
    similar_projects: SimilarProjects | None = None
    market_comparison: MarketComparison | None = None
    client_mode: ClientMode | None = None
    # What else a feature may need (catalog v6 blocks at a level); not chosen = not priced.
    scope: list[ScopeGroup] = []
    scope_source: str = ""
    research: Research | None = None
    reality_check: RealityCheck | None = None
    always_included: AlwaysIncluded | None = None
    independent_check: IndependentCheck | None = None
    size_check: SizeCheck | None = None
    client_provided: ClientProvided | None = None
    # catalog key -> plain words, for the standard blocks the form lets the user untick
    standard_blocks: dict[str, StandardBlock] = {}
    # the form's "Not mentioned: do you need these?" shortlist (feature keys, at most 8)
    commonly_needed: list[str] = Field(default=[], max_length=8)
    cms_built_in: CmsBuiltIn | None = None  # what a CMS already has (OPEN_QUESTIONS 154)

    @model_validator(mode="after")
    def _client_provided(self) -> "QuickConfig":
        for item in self.client_provided.items if self.client_provided else []:
            question = self.questions.get(item.question)
            if question is None:
                raise ValueError(f"client_provided: unknown question {item.question!r}")
            question.option(item.value)  # raises when the option does not exist
        return self

    @model_validator(mode="after")
    def _commonly_needed(self) -> "QuickConfig":
        unknown = set(self.commonly_needed) - {f.key for f in self.features}
        if unknown:
            raise ValueError(f"commonly_needed: unknown features {sorted(unknown)}")
        return self

    @model_validator(mode="after")
    def _support_terms(self) -> "QuickConfig":
        terms = self.support_terms
        if terms is None:
            return self
        for value in terms.values.values():
            self.questions["support_hours"].option(value)  # raises when it does not exist
        return self

    @model_validator(mode="after")
    def _cms_built_in(self) -> "QuickConfig":
        rule = self.cms_built_in
        if rule is None:
            return self
        unknown = set(rule.features) - {f.key for f in self.features}
        if unknown:
            raise ValueError(f"cms_built_in: unknown features {sorted(unknown)}")
        build_types = {o.value for o in self.questions["build_type"].options}
        if set(rule.build_types) - build_types:
            raise ValueError(f"cms_built_in: unknown build types {rule.build_types}")
        return self

    @model_validator(mode="after")
    def _scope_keys(self) -> "QuickConfig":
        keys = [i.key for g in self.scope for i in g.items]
        if len(keys) != len(set(keys)):
            raise ValueError("scope item keys must be unique")
        features = {f.key for f in self.features}
        standard = {k for t in self.sizing.tiers for k in t.base_components}
        smallest = min(self.sizing.levels, key=lambda k: self.sizing.levels[k].points)
        for g in self.scope:
            if g.feature is not None and g.feature not in features:
                raise ValueError(f"scope group {g.key}: unknown feature {g.feature!r}")
            for i in g.items:
                raised = [k for k, lv in i.adds.items() if k in standard and lv != smallest]
                if raised:  # a size step is a larger module, not the item's own increment
                    raise ValueError(f"scope item {i.key}: may not make {raised} bigger")
        return self

    def standard_keys(self) -> list[str]:
        """Every block that can be standard: the size tiers' and those answers add."""
        keys = [k for t in self.sizing.tiers for k in t.base_components]
        keys += [k for q in self.questions.values() for o in q.options for k in o.extra_components]
        return list(dict.fromkeys(keys))

    def scope_item(self, key: str) -> tuple[ScopeGroup, ScopeItem]:
        for g in self.scope:
            for i in g.items:
                if i.key == key:
                    return g, i
        raise ValueError(f"unknown scope item {key!r}")

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

"""Reference data the engine prices against: taxonomy, component catalog, rate card and
engine parameters. These are loaded from versioned seed YAML (`backend/seeds/`) and stored in
the database; an estimate snapshots the exact versions it used.

Every record carries a `source`. The value `placeholder` means "not yet calibrated against
real data"; using any placeholder marks an estimate as uncalibrated.
"""

import re
from datetime import date
from decimal import Decimal
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

PLACEHOLDER = "placeholder"
_VERSION = re.compile(r"^(.*?)(\d+)(.*)$")


def version_key(version: str) -> tuple[str, int, str]:
    """Natural order for version names: v9 < v10, us-v2 < us-v10 (plain text sorts v10 first)."""
    m = _VERSION.match(version)
    return (m.group(1), int(m.group(2)), m.group(3)) if m else (version, 0, "")


class Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class Sourced(Frozen):
    source: str = Field(min_length=1)


# --- enums shared by inputs and reference data -----------------------------------------------


class Size(StrEnum):
    S = "S"
    M = "M"
    L = "L"


class Complexity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


class TaskType(StrEnum):
    ANALYSIS = "analysis"
    ARCHITECTURE = "architecture"
    UI_DESIGN = "ui_design"
    CRUD = "crud"
    INTEGRATION = "integration"
    AI_ENGINEERING = "ai_engineering"
    DATA_MIGRATION = "data_migration"
    TESTS = "tests"
    SECURITY_TESTING = "security_testing"
    DEVOPS = "devops"
    DOCUMENTATION = "documentation"
    REVIEW_UAT = "review_uat"
    PM = "pm"
    TRAINING = "training"


class Driver(StrEnum):
    """NFR drivers a catalog component can be sensitive to."""

    UPTIME_SLA = "uptime_sla"
    SECURITY_LEVEL = "security_level"
    LANGUAGES = "languages"
    ACCESSIBILITY = "accessibility"
    CONCURRENCY = "concurrency"


# --- taxonomy --------------------------------------------------------------------------------


class Stage(Frozen):
    key: str
    name: str
    order: int


class Bucket(Frozen):
    key: str  # "<stage>.<name>", e.g. "build.integrations"
    stage: str
    name: str
    order: int
    gst_percent: Decimal | None = None  # None -> commercial.gst_percent default


class Taxonomy(Sourced):
    version: str
    stages: list[Stage]
    buckets: list[Bucket]

    @model_validator(mode="after")
    def _check(self) -> "Taxonomy":
        stage_keys = {s.key for s in self.stages}
        for b in self.buckets:
            if b.stage not in stage_keys or not b.key.startswith(f"{b.stage}."):
                raise ValueError(f"bucket {b.key} has invalid stage {b.stage}")
        return self

    def bucket(self, key: str) -> Bucket:
        for b in self.buckets:
            if b.key == key:
                return b
        raise KeyError(f"unknown taxonomy bucket {key!r}")


# --- component catalog -----------------------------------------------------------------------


class ComponentLicence(Frozen):
    rate_key: str  # annual licence rate item used when licensing == "licensed"
    effort_factor: Decimal = Field(gt=0, le=1)  # build effort multiplier with the licensed product


class BaselineEra(StrEnum):
    """Whether the effort data behind a component was measured with AI coding tools in use."""

    PRE_AI = "pre_ai"  # workflows that did not materially use AI coding tools
    AI_ASSISTED = "ai_assisted"  # observed with AI coding tools already in use
    UNKNOWN = "unknown"  # AI use cannot be established


class EraBasis(StrEnum):
    """Why an evidence item has its era. A date is only a provisional heuristic; an explicit
    statement or a documented workflow takes precedence."""

    EXPLICIT_STATEMENT = "explicit_statement"
    DOCUMENTED_WORKFLOW = "documented_workflow"
    DATE_HEURISTIC = "date_heuristic"
    NOT_ESTABLISHED = "not_established"


Quality = Literal["low", "low_medium", "medium", "high"]


class EffortEvidence(Frozen):
    """One cited source behind a component's effort figures (catalog v6+)."""

    id: str
    citation: str = Field(min_length=1)
    source_type: Literal[
        "measured_projects",
        "published_dataset",
        "published_study",
        "vendor_estimate",
        "expert_judgement",
    ]
    published: int | None = None  # year the data was published or measured; None = undated
    url: str | None = None  # where the figure can be checked (catalog v7+)
    era: BaselineEra
    era_basis: EraBasis
    ai_workflow: str | None = None  # AI tools and practice, when the source states them
    sample_size: int | None = Field(default=None, ge=1)
    quality: Quality

    @model_validator(mode="after")
    def _check(self) -> "EffortEvidence":
        if self.era is BaselineEra.AI_ASSISTED and self.era_basis not in {
            EraBasis.EXPLICIT_STATEMENT,
            EraBasis.DOCUMENTED_WORKFLOW,
        }:
            raise ValueError(f"{self.id}: ai_assisted needs an explicit statement or workflow")
        if self.era_basis is EraBasis.DATE_HEURISTIC and (
            self.era is not BaselineEra.PRE_AI or self.published is None
        ):
            raise ValueError(f"{self.id}: a date heuristic can only give pre_ai, with a year")
        if self.era_basis is EraBasis.NOT_ESTABLISHED and self.era is not BaselineEra.UNKNOWN:
            raise ValueError(f"{self.id}: an era that is not established is unknown")
        return self


def derived_era(evidence: list[EffortEvidence]) -> BaselineEra:
    """pre_ai only if every source is pre_ai; ai_assisted only if every source is; else unknown."""
    eras = {e.era for e in evidence}
    if eras == {BaselineEra.PRE_AI}:
        return BaselineEra.PRE_AI
    if eras == {BaselineEra.AI_ASSISTED}:
        return BaselineEra.AI_ASSISTED
    return BaselineEra.UNKNOWN


class CatalogComponent(Sourced):
    key: str
    name: str
    category: str
    bucket: str
    description: str = ""
    task_mix: dict[TaskType, Decimal]
    base_effort_pd: dict[Size, Decimal]
    applicable_drivers: list[Driver] = []
    tags: list[Literal["integration", "ai", "data_migration"]] = []
    licence: ComponentLicence | None = None
    # Catalog v7+: the tech-stack section it belongs to (one of the catalog's `sections`), so a
    # reader can look at the relevant sections first. Never used in pricing.
    section: str | None = None
    # Catalog v6+: where the effort figures come from. None (catalogs v1-v5) prices as before:
    # AI savings on every task. Otherwise the era must follow from the evidence (derived_era).
    source_era: BaselineEra | None = None
    era_reason: str = ""
    confidence: Quality | None = None
    evidence: list[EffortEvidence] = []

    @model_validator(mode="after")
    def _check(self) -> "CatalogComponent":
        if sum(self.task_mix.values()) != Decimal(1):
            raise ValueError(f"{self.key}: task_mix must sum to 1")
        if set(self.base_effort_pd) != set(Size):
            raise ValueError(f"{self.key}: base_effort_pd needs S, M and L")
        e = self.base_effort_pd
        if not (Decimal(0) < e[Size.S] <= e[Size.M] <= e[Size.L]):
            raise ValueError(f"{self.key}: base effort must satisfy 0 < S <= M <= L")
        if self.source_era is None:
            if self.evidence:
                raise ValueError(f"{self.key}: evidence needs a source_era")
        elif not self.evidence:
            raise ValueError(f"{self.key}: source_era needs at least one evidence item")
        elif self.source_era is not derived_era(self.evidence):
            raise ValueError(f"{self.key}: source_era must be {derived_era(self.evidence)}")
        return self


class EraRules(Frozen):
    """How evidence eras are set (catalog v6+). The cutoff is a provisional heuristic."""

    pre_ai_before_year: int  # data published / measured before this year may be dated pre_ai
    source: str = Field(min_length=1)


class CalibrationBasis(Frozen):
    """What the effort level of these figures was calibrated against (documentation only: the
    engine never reads it). Kept apart from the source era: a calibration against pre-AI data
    does not make a component's own sources pre-AI."""

    parameter: str  # the dial it explains, e.g. "calibration.effort_multiplier"
    parameter_sets: list[str]
    method: str
    data: str
    reproducible: bool
    limitations: list[str]
    source: str = Field(min_length=1)


class Catalog(Frozen):
    version: str
    components: list[CatalogComponent]
    # Seed-file notes (catalog v6+). The database mirror stores components only.
    era_rules: EraRules | None = None
    calibration_basis: CalibrationBasis | None = None
    sections: dict[str, str] = {}  # catalog v7+: section key -> label; every component in one

    @model_validator(mode="after")
    def _check_dates(self) -> "Catalog":
        if self.sections:
            for c in self.components:
                if c.section not in self.sections:
                    raise ValueError(f"{c.key}: section {c.section!r} is not a catalog section")
        if self.era_rules is None:
            return self
        for c in self.components:
            for e in c.evidence:
                dated = e.era_basis is EraBasis.DATE_HEURISTIC
                if dated and (e.published or 0) >= self.era_rules.pre_ai_before_year:
                    raise ValueError(f"{e.id}: too recent to be dated pre_ai")
        return self

    def get(self, key: str) -> CatalogComponent:
        for c in self.components:
            if c.key == key:
                return c
        raise KeyError(f"unknown catalog component {key!r}")


# --- rate card -------------------------------------------------------------------------------


class RateKind(StrEnum):
    ROLE = "role"
    CLOUD_SKU = "cloud_sku"
    LLM_TOKEN = "llm_token"
    GPU_HOUR = "gpu_hour"
    LICENCE = "licence"
    AUDIT_FEE = "audit_fee"
    BANK_CHARGE = "bank_charge"
    OTHER = "other"


class RateItem(Sourced):
    key: str
    kind: RateKind
    unit: str
    amount: Decimal = Field(ge=0)  # major units of `currency` (or a ratio for unit "ratio_*")
    currency: str = "INR"
    region: str | None = None
    source_url: str | None = None


class RateCard(Sourced):
    version: str
    effective_date: date
    region: str = "india"  # which country's estimates this card prices
    currency: str = "INR"  # estimate currency; other-currency items are converted via forex
    status: Literal["draft", "active", "retired"] = "active"
    items: list[RateItem]

    @model_validator(mode="after")
    def _unique(self) -> "RateCard":
        keys = [i.key for i in self.items]
        dupes = {k for k in keys if keys.count(k) > 1}
        if dupes:
            raise ValueError(f"duplicate rate keys: {sorted(dupes)}")
        return self


# --- engine parameters -----------------------------------------------------------------------


class Point(Frozen):
    x: Decimal
    y: Decimal


class SizeBand(Frozen):
    name: str
    max_build_pd: Decimal | None  # None = open-ended top band
    pm_fte: Decimal
    om_pm_fte: Decimal
    exit_management_pd: Decimal
    audit_band: str


class Calendar(Sourced):
    pd_per_month: Decimal
    pd_per_year: Decimal
    hours_per_month: Decimal
    hours_per_year: Decimal
    days_per_year: Decimal
    seconds_per_day: Decimal


class ConcurrencyBand(Frozen):
    name: str
    max_peak_users: int | None
    multiplier: Decimal
    db_tier: str


class NfrMultipliers(Sourced):
    uptime_sla: dict[str, Decimal]
    security_level: dict[str, Decimal]
    per_additional_language: Decimal
    languages_cap: Decimal
    accessibility: dict[str, Decimal]  # "true"/"false"
    concurrency_bands: list[ConcurrencyBand]
    # v17+: components that build accessibility as their own work; when the project has one,
    # the accessibility factor is not applied to the other components as well.
    accessibility_components: list[str] = []
    # v19+: the same for languages (a multilingual framework component)
    languages_components: list[str] = []


class AiProductivity(Sourced):
    task_savings: dict[TaskType, Decimal]
    maturity_scale: dict[str, Decimal]
    max_saving: Decimal
    # v12+: extra review of AI-written code, as a share of the effort AI saves, by this role.
    review_share_of_saved: Decimal | None = Field(default=None, ge=0, le=1)
    review_role: str | None = None
    # v20+: the review of AI-written code is shared between roles like other review work
    # (task_roles for this task, e.g. review_uat: 0.7 developer / 0.3 senior developer);
    # None = all of it by review_role.
    review_task: TaskType | None = None
    # v18+: effort data of unknown era counts as pre-AI (the hours are calibrated against
    # finished pre-AI projects), so the team's AI savings apply to it in the estimate itself.
    unknown_era_is_pre_ai: bool = False
    # v20+: a source for one field that differs from the group's, e.g.
    # {review_share_of_saved: placeholder}; the trace and the calibration status use it.
    field_sources: dict[str, str] = {}


class Reuse(Sourced):
    """v19+: what the build reuses (questionnaire build_type). A CMS or a framework that
    generates the admin screens shrinks only the listed task shares; a build type without a
    factor (custom, ready_product) keeps 1."""

    tasks: list[TaskType]
    factor_by_build_type: dict[str, Decimal]
    # v20+: tasks that check the build (review, tests) and shrink in proportion to it: a
    # component's follow tasks × (its other work after reuse / before reuse).
    follow_tasks: list[TaskType] = []
    # v20+: components that test the whole system (e.g. functional testing and UAT): their
    # follow tasks use the project's ratio (all build-stage components) instead of their own.
    project_wide_components: list[str] = []

    @model_validator(mode="after")
    def _factors(self) -> "Reuse":
        if any(not Decimal(0) < f <= Decimal(1) for f in self.factor_by_build_type.values()):
            raise ValueError("reuse factors must be in (0, 1]")
        if set(self.follow_tasks) & set(self.tasks):
            raise ValueError("a reuse task cannot also follow the reused work")
        return self


class EffortCaps(Sourced):
    """v20+: ceilings on work that tends to grow out of proportion with the build, applied to
    the summed component effort before pricing (each cap scales its tasks down, never up):

      base     = Σ build-stage component effort on base_tasks
      review   ≤ review_max_share[size] × base    (review_task, every component)
      pre-build ≤ pre_build_max_share[size] × base (every task of pre-build components)
      architect ≤ floor + architecture_pd_per_hard_problem × hard problems
                                                   (architecture_task, after the pre-build cap)
      floor    = max(architecture_base_pd, architecture_max_share_by_size[size] × base)
                 when the size is listed, else architecture_base_pd

    The shares by project size (`*_by_size`, keys as the answer project_size) replace the flat
    share when the size is known and listed: review, integration and design overhead grows with
    size.
    """

    base_tasks: list[TaskType]
    review_task: TaskType
    review_max_share: Decimal = Field(gt=0)
    pre_build_max_share: Decimal = Field(gt=0)
    architecture_task: TaskType
    architecture_base_pd: Decimal = Field(ge=0)
    architecture_pd_per_hard_problem: Decimal = Field(ge=0)
    review_max_share_by_size: dict[str, Decimal] = {}
    pre_build_max_share_by_size: dict[str, Decimal] = {}
    architecture_max_share_by_size: dict[str, Decimal] = {}

    @model_validator(mode="after")
    def _base(self) -> "EffortCaps":
        if {self.review_task, self.architecture_task} & set(self.base_tasks):
            raise ValueError("a capped task cannot be part of the base it is capped against")
        return self


class Timeline(Sourced):
    min_duration_months: Decimal
    max_team_curve: list[Point]  # x = build effort person-months, y = max team size
    size_bands: list[SizeBand]
    compression_curve: list[Point]  # x = deadline/natural ratio, y = cost multiplier
    infeasible_below_ratio: Decimal
    duration_quantum_months: Decimal
    # v17+: a squeezed build also runs its programme (management, test servers) over the
    # deadline, not the natural duration it was squeezed from.
    programme_follows_deadline: bool = False


class Programme(Sourced):
    pm_role: str
    steering_interval_months: Decimal
    steering_rate_key: str
    mis_pd_per_month: Decimal
    mis_role: str
    travel_trips_per_month: Decimal
    travel_rate_key: str
    non_prod_environments: Decimal
    environment_rate_key: str
    # v17+: test servers priced on the same provider as production, by hosting provider.
    environment_rate_key_by_provider: dict[str, str] = {}


class OnPrem(Sourced):
    server_rate_key: str
    storage_tb_rate_key: str
    colocation_rate_key: str
    servers_per_rack: Decimal
    hw_amc_percent: Decimal


class Hosting(Sourced):
    pattern_by_sla: dict[str, Literal["single", "ha", "ha_dr"]]
    concurrent_users_per_vcpu: Decimal
    vcpu_per_app_server: Decimal
    min_app_servers: dict[str, Decimal]
    # v12+: when the peak needs at most this many vCPUs, servers are priced at the provider's
    # small server rate (`cloud.<provider>.app_server_small.month`) when the rate card has one.
    small_app_server_max_vcpus: Decimal | None = None
    db_instances: dict[str, Decimal]
    base_storage_gb: Decimal
    db_storage_gb: Decimal
    backup_factor: Decimal
    monthly_active_share: Decimal
    transfer_mb_per_active_user_month: Decimal
    dr_cost_factor: Decimal
    reserved_discount: dict[str, Decimal]
    forex_rate_key: str
    forex_buffer: Decimal
    mb_per_gb: Decimal
    gb_per_tb: Decimal
    on_prem: OnPrem


class AiRuntime(Sourced):
    token_input_rate_key: str
    token_output_rate_key: str
    tokens_per_unit: Decimal  # token prices are quoted per this many tokens
    volume_growth_per_year: Decimal
    annual_price_change: Decimal
    gpu_rate_key: str
    # Smaller, cheaper model for simple chatbots (parameter sets v7+); None = one tier only.
    simple_token_input_rate_key: str | None = None
    simple_token_output_rate_key: str | None = None
    peak_factor: Decimal
    queries_per_second_per_gpu: Decimal
    min_gpus: dict[str, Decimal]


class HelpdeskTier(Frozen):
    max_users: int | None
    seats: Decimal


class Maintenance(Sourced):
    helpdesk_seats_by_users: list[HelpdeskTier]
    helpdesk_coverage_fte: dict[str, Decimal]  # by support SLA
    helpdesk_role: str
    bugfix_share_of_build_pd: Decimal
    bugfix_role: str
    patching_share_of_build_pd: Decimal
    patching_role: str
    upgrade_share_of_build_pd: Decimal
    upgrade_role: str
    change_request_share_of_build_pd: Decimal
    change_request_role: str
    annual_audit_rate_prefix: str
    ssl_rate_key: str
    domain_rate_key: str
    rule_of_thumb_low: Decimal
    rule_of_thumb_high: Decimal
    # v19+: the domain rate by the address the document names (questionnaire web_domain), e.g.
    # a free .gov.in address only when the document asks for one; empty = domain_rate_key.
    domain_rate_key_by_type: dict[str, str] = {}
    # v20+: the SSL rate by certificate type (questionnaire ssl_type): a free domain-validated
    # one unless the document asks for an organisation-validated one; empty = ssl_rate_key.
    ssl_rate_key_by_type: dict[str, str] = {}


class GoLive(Sourced):
    cert_in_audit_rate_prefix: str
    cert_in_reaudit_rate_prefix: str
    stqc_rate_key: str
    trainer_role: str
    training_pd_per_session: Decimal
    travel_rate_key: str
    trips_per_outstation_session: Decimal
    hypercare_team_fte: dict[str, Decimal]
    pd_per_week: Decimal


class Escalation(Sourced):
    labour: Decimal
    prices: Decimal


class Commercial(Sourced):
    tax_label: str = "GST"
    cost_of_capital: Decimal
    pbg_rate_key: str
    payment_delay_months: Decimal
    ld_reserve_build_percent: Decimal
    penalty_reserve_run_percent: dict[str, Decimal]  # by support SLA
    contingency_at_clarity: list[Point]  # x = clarity 1..5, y = contingency fraction
    exit_role: str
    gst_percent: Decimal
    # v19+: the penalty reserve only when the contract has a penalty clause (questionnaire
    # penalty_clause, cited from the document); False = always, as before.
    penalty_needs_clause: bool = False


class ClaritySpread(Frozen):
    down: Decimal
    up: Decimal


class Uncertainty(Sourced):
    default_clarity: Decimal
    clarity_spread: dict[int, ClaritySpread]
    template_match_extra_up: dict[str, Decimal]
    tag_extra_up: dict[str, Decimal]
    compression_extra_up_per_unit: Decimal
    om_extra_up_per_year: Decimal
    hosting: ClaritySpread
    ai_runtime: ClaritySpread
    fixed_fee: ClaritySpread
    monte_carlo_runs: int
    distribution: Literal["triangular"]
    # v19+: extra spread on a component that holds a hard problem (concurrency, money movement,
    # legacy data...): the range widens, the planned cost does not change.
    hard_problem_extra: ClaritySpread | None = None


class Confidence(Sourced):
    weight_clarity: Decimal
    weight_template: Decimal
    weight_freshness: Decimal
    template_score: dict[str, Decimal]
    fresh_days: int
    stale_days: int
    high_threshold: Decimal
    medium_threshold: Decimal


class TaskRoles(Sourced):
    roles: dict[TaskType, str]
    # v19+: a task shared by several roles, e.g. review: {role.developer: 0.7,
    # role.senior_developer: 0.3} (peer review and sign-off); used instead of `roles` there.
    split: dict[TaskType, dict[str, Decimal]] = {}

    @model_validator(mode="after")
    def _shares(self) -> "TaskRoles":
        if any(sum(shares.values()) != Decimal(1) for shares in self.split.values()):
            raise ValueError("task_roles.split shares must sum to 1")
        return self


class SegmentBacktest(Frozen):
    """How a buyer segment's prices performed on real projects."""

    projects: int = Field(ge=0)
    within_25_percent: int = Field(ge=0)  # within ±25% of the price paid, or inside its band
    note: str = ""


class MarketBand(Frozen):
    """Real contract prices of one project size as multiples of our estimate (P50): the middle
    half (P25-P75) and the median, from the back-test."""

    projects: int = Field(ge=0)
    low: Decimal = Field(gt=0)
    mid: Decimal = Field(gt=0)
    high: Decimal = Field(gt=0)


class Calibration(Sourced):
    """Global dials tuned by back-testing against real contract values (and adjustable per
    company in Settings): effort_multiplier scales every component's base effort;
    run_multiplier scales O&M support labour (helpdesk, bug-fix, patching, upgrades, CRs)."""

    effort_multiplier: Decimal = Field(default=Decimal(1), gt=0)
    run_multiplier: Decimal = Field(default=Decimal(1), gt=0)
    notes: str = ""
    segment_effort_multiplier: dict[str, Decimal] = {}  # e.g. {small_business: 0.3}
    segment_run_multiplier: dict[str, Decimal] = {}
    segment_backtest: dict[str, SegmentBacktest] = {}
    # Build-effort factor by project size (small / medium / large), applied after the buyer
    # segment factor; and how each size performed on real projects.
    size_effort_multiplier: dict[str, Decimal] = {}
    # v13+: build-effort factor by feature points (x = points, y = factor, straight lines in
    # between), used instead of size_effort_multiplier when the estimate has size_points.
    size_points_curve: list[Point] = []
    # Segment factor for one size only, replacing segment_effort_multiplier there,
    # e.g. {small_business: {small: 2.6}} (where a segment's data covers one size).
    segment_size_effort_multiplier: dict[str, dict[str, Decimal]] = {}
    size_backtest: dict[str, SegmentBacktest] = {}
    # Build-effort factor by any questionnaire answer, e.g. {build_type: {ready_product: 0.3}}.
    answer_effort_multiplier: dict[str, dict[str, Decimal]] = {}
    # How the set did on projects it was not tuned on (the honest accuracy figure).
    holdout_projects: int = 0
    holdout_median_abs_error_percent: Decimal | None = None
    # Shared model error by buyer segment, from back-test residuals: every base line in a
    # simulation run is multiplied by one draw of triangular(1 − down, 1, 1 + up).
    model_spread: dict[str, ClaritySpread] = {}
    # v12+: the same by project size (used instead of the segment's when the size is known).
    model_spread_by_size: dict[str, ClaritySpread] = {}
    # v14+ (should-cost): the price is not tuned to market prices; what real contracts of each
    # project size cost relative to it is shown next to it as a market check.
    should_cost: bool = False
    market_by_size: dict[str, MarketBand] = {}
    backtest_projects: int = 0  # real published contracts it was tested on
    median_abs_error_percent: Decimal | None = None  # typical miss on those contracts


class UsageService(Frozen):
    """A third-party service billed by use or by subscription (SMS, email, maps, eKYC, app
    stores, web firewall...). Priced only when its conditions hold:
    `components` (any one in scope; empty = always), `segments` (buyer segments; empty = all),
    `regions` (estimate country; empty = all), `min_users` and `needs_cloud_hosting`.

    basis:
      monthly   max(0, users × active_share × units_per_active_user_month − free_units_per_month)
                × months_per_year
      per_user  users × (first_year_units_per_user in year 1 else later_year_units_per_user)
      fixed     count × periods (12 if rate_period = month, else 1; one_off only in year 1)
    cost = units × rate / per_units × (1 + escalation_prices)^year
    """

    key: str
    label: str
    rate_key: str
    basis: Literal["monthly", "per_user", "fixed"]
    per_units: Decimal = Field(default=Decimal(1), gt=0)  # the rate is quoted per this many
    components: list[str] = []
    segments: list[str] = []
    regions: list[str] = []
    min_users: int = 0
    needs_cloud_hosting: bool = False
    units_per_active_user_month: Decimal = Decimal(0)
    free_units_per_month: Decimal = Decimal(0)
    first_year_units_per_user: Decimal = Decimal(0)
    later_year_units_per_user: Decimal = Decimal(0)
    count: Decimal = Decimal(1)
    rate_period: Literal["month", "year", "one_off"] = "year"


class AiFeatureRuntime(Frozen):
    """Running cost of AI features other than the chatbot (summaries, classification, OCR...):
    instances × users × active_share × calls_per_active_user_month × months_per_year
    × (tokens_in × price_in + tokens_out × price_out) / tokens_per_unit."""

    components: list[str]
    calls_per_active_user_month: Decimal
    tokens_in_per_call: Decimal
    tokens_out_per_call: Decimal


class DevTools(Frozen):
    """Build-phase tool subscriptions, one seat per person-month of build effort:
    AI coding assistant (only when the team uses AI tools) and the core dev tools suite."""

    ai_coding_rate_key: str
    dev_suite_rate_key: str


class Translation(Frozen):
    """Human translation of on-screen content into each extra language: words =
    words_per_component × components; one-off = words × (languages − 1) × rate_per_word;
    each later year = one-off × annual_update_share."""

    rate_key: str
    words_per_component: Decimal
    annual_update_share: Decimal


class ClientPaidNote(Frozen):
    """A cost the client pays directly to a third party (not part of the quote), shown as a
    rate: e.g. the payment gateway's fee on each online payment."""

    key: str
    label: str
    components: list[str] = []
    rate_keys: list[str]  # quoted in the note, in this order
    text: str  # with {0}, {1}... for the rate amounts


class ThirdParty(Sourced):
    """Third-party running costs, build tools and client-paid items (parameter sets v5+)."""

    services: list[UsageService] = []
    ai_features: AiFeatureRuntime | None = None
    dev_tools: DevTools | None = None
    translation: Translation | None = None
    client_paid_notes: list[ClientPaidNote] = []


class Lean(Sourced):
    """Lean delivery for private and small-business projects (parameter sets v6+): management
    and hypercare scale with the work instead of the calendar, and test environments are priced
    as one small cloud server each.

      build PM pd    = min(pm_fte × months × pd_per_month, pm_share_of_build_pd × build_pd)
      hypercare pd   = min(weeks × pd_per_week × Σ fte, hypercare_share_of_build_pd × build_pd)
      O&M PM pd/year = min(om_pm_fte × pd_per_year, om_pm_share_of_build_pd × build_pd)
    """

    segments: list[str]
    sizes: list[str] = []  # project sizes that are delivered lean whatever the buyer
    # v13+: lean whenever no formal reports and review meetings are asked for (the project
    # manager's time follows the work), whatever the size.
    unless_governance: bool = False
    pm_share_of_build_pd: Decimal = Field(gt=0, le=1)
    hypercare_share_of_build_pd: Decimal = Field(gt=0, le=1)
    om_pm_share_of_build_pd: Decimal = Field(gt=0, le=1)
    environment_rate_key: str | None = None


class Defaults(Sourced):
    """Questionnaire defaults, used (and listed as assumptions) when the user gives no answer."""

    values: dict[str, object]


class ParameterSet(Frozen):
    version: str
    effective_date: date
    region: str = "india"
    status: Literal["draft", "active", "retired"] = "active"
    calendar: Calendar
    complexity_multipliers: dict[Complexity, Decimal]
    complexity_source: str
    nfr: NfrMultipliers
    ai_productivity: AiProductivity
    reuse: Reuse | None = None  # None (older sets): every build priced as written from scratch
    effort_caps: EffortCaps | None = None  # None (older sets): no ceilings
    task_roles: TaskRoles
    timeline: Timeline
    programme: Programme
    hosting: Hosting
    ai_runtime: AiRuntime
    maintenance: Maintenance
    go_live: GoLive
    escalation: Escalation
    commercial: Commercial
    uncertainty: Uncertainty
    confidence: Confidence
    defaults: Defaults
    calibration: Calibration | None = None
    third_party: ThirdParty | None = None  # None (older sets): no third-party lines
    lean: Lean | None = None  # None (older sets): calendar-based management for everyone

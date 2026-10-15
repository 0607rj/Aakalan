"""Reference data the engine prices against: taxonomy, component catalog, rate card and
engine parameters. These are loaded from versioned seed YAML (`backend/seeds/`) and stored in
the database; an estimate snapshots the exact versions it used.

Every record carries a `source`. The value `placeholder` means "not yet calibrated against
real data"; using any placeholder marks an estimate as uncalibrated.
"""

from datetime import date
from decimal import Decimal
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

PLACEHOLDER = "placeholder"


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

    @model_validator(mode="after")
    def _check(self) -> "CatalogComponent":
        if sum(self.task_mix.values()) != Decimal(1):
            raise ValueError(f"{self.key}: task_mix must sum to 1")
        if set(self.base_effort_pd) != set(Size):
            raise ValueError(f"{self.key}: base_effort_pd needs S, M and L")
        e = self.base_effort_pd
        if not (Decimal(0) < e[Size.S] <= e[Size.M] <= e[Size.L]):
            raise ValueError(f"{self.key}: base effort must satisfy 0 < S <= M <= L")
        return self


class Catalog(Frozen):
    version: str
    components: list[CatalogComponent]

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


class AiProductivity(Sourced):
    task_savings: dict[TaskType, Decimal]
    maturity_scale: dict[str, Decimal]
    max_saving: Decimal


class Timeline(Sourced):
    min_duration_months: Decimal
    max_team_curve: list[Point]  # x = build effort person-months, y = max team size
    size_bands: list[SizeBand]
    compression_curve: list[Point]  # x = deadline/natural ratio, y = cost multiplier
    infeasible_below_ratio: Decimal
    duration_quantum_months: Decimal


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
    cost_of_capital: Decimal
    pbg_rate_key: str
    payment_delay_months: Decimal
    ld_reserve_build_percent: Decimal
    penalty_reserve_run_percent: dict[str, Decimal]  # by support SLA
    contingency_at_clarity: list[Point]  # x = clarity 1..5, y = contingency fraction
    exit_role: str
    gst_percent: Decimal


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


class Defaults(Sourced):
    """Questionnaire defaults, used (and listed as assumptions) when the user gives no answer."""

    values: dict[str, object]


class ParameterSet(Frozen):
    version: str
    effective_date: date
    status: Literal["draft", "active", "retired"] = "active"
    calendar: Calendar
    complexity_multipliers: dict[Complexity, Decimal]
    complexity_source: str
    nfr: NfrMultipliers
    ai_productivity: AiProductivity
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

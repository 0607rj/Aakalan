"""Engine inputs. `EstimateInput` is a complete, self-contained snapshot: given the same
snapshot (including seed) the engine returns an identical result (rule 3). It is stored as
JSON on every Estimate row."""

from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.services.engine.reference import (
    Catalog,
    Complexity,
    ParameterSet,
    RateCard,
    Size,
    Taxonomy,
)


class Strict(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class SourceRef(Strict):
    """Where a requirement comes from in the tender document."""

    clause_ref: str
    page: int | None = None
    document: str | None = None
    chunk_id: str | None = None


class RequirementIn(Strict):
    id: str
    code: str
    text: str
    category: str
    clarity_score: int = Field(ge=1, le=5)
    source_refs: list[SourceRef] = []


class ComponentInstanceIn(Strict):
    id: str
    catalog_key: str
    label: str | None = None
    size: Size
    complexity: Complexity = Complexity.MEDIUM
    quantity: int = Field(default=1, ge=1)
    requirement_ids: list[str] = []
    # Holds a hard problem the document describes (concurrency, money movement, legacy data,
    # ...): a wider range (uncertainty.hard_problem_extra) and no reuse discount (v19+).
    hard_problem: bool = False


class OnsiteResource(Strict):
    role: str = Field(pattern=r"^role\.[a-z_]+$")  # rate key, e.g. "role.developer"
    count: Decimal = Field(gt=0)
    # person-days each in all, when the document limits onsite work (e.g. during an event);
    # None = all year, every support year
    days: Decimal | None = Field(default=None, gt=0)


class PaymentMilestone(Strict):
    at_build_fraction: Decimal = Field(ge=0, le=1)
    offset_months: Decimal = Field(default=Decimal(0), ge=0)
    percent: Decimal = Field(gt=0, le=1)


class Questionnaire(Strict):
    """Project drivers. Every field is required here; `resolve_questionnaire` fills gaps from
    `ParameterSet.defaults` and records each default as an assumption."""

    om_years: int = Field(ge=0, le=10)
    team_ai_maturity: Literal["none", "low", "medium", "high"]  # none = no AI tools
    deadline_months: Decimal | None = Field(gt=0)
    uptime_sla: Literal["99.0", "99.5", "99.9", "99.95"]
    security_level: Literal["standard", "high", "very_high"]
    languages: int = Field(ge=1)
    gigw_accessibility: bool
    users_total: int = Field(ge=0)
    peak_concurrent_users: int = Field(ge=0)
    documents_per_month: int = Field(ge=0)
    avg_document_mb: Decimal = Field(ge=0)
    chatbot_queries_per_day: int = Field(ge=0)
    tokens_in_per_query: int = Field(ge=0)
    tokens_out_per_query: int = Field(ge=0)
    hosting_provider: Literal["aws", "indian_cloud", "on_prem"]
    hosting_pricing: Literal["on_demand", "reserved"]
    ai_runtime_mode: Literal["api", "self_hosted_gpu"]
    licensing: Literal["open_source", "licensed"]
    support_sla: Literal["8x5", "24x7"]
    onsite_resources: list[OnsiteResource]
    change_request_pd_per_year: Decimal | None = Field(ge=0)
    cert_in_audit: bool
    stqc_certification: bool
    training_sessions: int = Field(ge=0)
    training_outstation_sessions: int = Field(ge=0)
    hypercare_weeks: int = Field(ge=0)
    emd_paise: int = Field(ge=0)
    emd_lock_months: Decimal = Field(ge=0)
    pbg_percent: Decimal = Field(ge=0, le=1)
    pbg_validity_months: Decimal | None = Field(ge=0)
    payment_schedule: list[PaymentMilestone]
    margin_percent: Decimal = Field(ge=0, le=1)
    contingency_percent: Decimal | None = Field(ge=0, le=1)
    gst_percent: Decimal | None = Field(ge=0, le=1)
    escalation_labour: Decimal | None = Field(ge=0, le=1)
    escalation_prices: Decimal | None = Field(ge=0, le=1)
    # Added after back-testing: in many government contracts the client provides hosting and
    # support is handled by the maintenance team. Defaults keep earlier parameter sets valid.
    hosting_in_scope: bool = True
    helpdesk_in_scope: bool = True
    # Government-style programme overheads (steering meetings, monthly MIS reports, travel);
    # private and small projects usually have none of these.
    governance_overheads: bool = True
    buyer_segment: Literal["government", "private", "small_business"] = "government"
    non_prod_environments: int | None = Field(default=None, ge=0, le=5)  # None = parameter
    # Third-party usage fees (SMS, email, maps, eKYC, AI features): in the quote, or paid by the
    # client directly to the providers.
    usage_fees_in_scope: bool = True
    # Which AI model the chatbot and AI features run on: a simple FAQ bot needs only a small,
    # cheap model (used when the parameter set prices one).
    ai_model_tier: Literal["advanced", "simple"] = "advanced"
    # Custom software, or a ready-made product (SaaS, WordPress, Shopify, a chatbot platform)
    # set up for the client: far less build work for the same features. cms / framework
    # (parameter sets v19+): custom work on a CMS (Drupal, WordPress) or on a framework that
    # generates the admin screens; only the screen and record-keeping work is smaller.
    build_type: Literal["custom", "framework", "cms", "ready_product"] = "custom"
    # A standby site in another place for disasters (recovery time / data-loss limits). High
    # uptime alone does not ask for one (parameter sets v17+).
    disaster_recovery: bool = False
    # Whether the contract has penalties for delay or downtime (a liquidated-damages or
    # service-level clause): with commercial.penalty_needs_clause (v19+) the penalty reserve is
    # priced only then.
    penalty_clause: bool = True
    # The web address: a .gov.in / .nic.in one (free from NIC) or a commercial one, priced by
    # maintenance.domain_rate_key_by_type (v19+).
    web_domain: Literal["gov_in", "commercial"] = "gov_in"
    # How big and deep the work is, independent of the feature list: the same features cost
    # far less as a simple website than as a state-wide system. None = no size factor.
    project_size: Literal["small", "small_medium", "medium", "medium_large", "large"] | None = None
    # How much is built, in feature points (basic 1, standard 2, advanced 4 per feature): with
    # a parameter set that has a size curve (v13+), the size factor follows the points smoothly
    # instead of jumping between project sizes. None = use project_size.
    size_points: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def _schedule(self) -> "Questionnaire":
        if self.payment_schedule and sum(m.percent for m in self.payment_schedule) != 1:
            raise ValueError("payment_schedule percentages must sum to 1")
        if self.training_outstation_sessions > self.training_sessions:
            raise ValueError("training_outstation_sessions cannot exceed training_sessions")
        return self


QUESTIONNAIRE_KEYS: tuple[str, ...] = tuple(Questionnaire.model_fields)


class AnswerIn(Strict):
    """A user's answer to one questionnaire key, optionally citing requirements (traceability)."""

    key: str
    value: object
    requirement_ids: list[str] = []


class ProjectInfo(Strict):
    name: str
    buyer_type: str
    domain: str


class EstimateInput(Strict):
    project: ProjectInfo
    as_of_date: date
    seed: int = Field(ge=0)
    template_match: Literal["none", "weak", "strong"] = "none"
    requirements: list[RequirementIn]
    components: list[ComponentInstanceIn]
    answers: list[AnswerIn] = []
    taxonomy: Taxonomy
    catalog: Catalog
    rate_card: RateCard
    parameters: ParameterSet
    monte_carlo_runs: int | None = Field(default=None, ge=100)
    # "pre_ai_sensitivity" prices unknown-era components as if their effort data were pre-AI
    # (AI savings applied): a second, labelled run beside the estimate, never the estimate.
    era_scenario: Literal["estimate", "pre_ai_sensitivity"] = "estimate"

    @model_validator(mode="after")
    def _refs(self) -> "EstimateInput":
        req_ids = {r.id for r in self.requirements}
        catalog_keys = {c.key for c in self.catalog.components}
        for c in self.components:
            if c.catalog_key not in catalog_keys:
                raise ValueError(f"component {c.id}: {c.catalog_key!r} not in catalog")
            missing = set(c.requirement_ids) - req_ids
            if missing:
                raise ValueError(f"component {c.id} links unknown requirements {sorted(missing)}")
        keys = [a.key for a in self.answers]
        unknown = set(keys) - set(QUESTIONNAIRE_KEYS)
        if unknown:
            raise ValueError(f"unknown questionnaire keys {sorted(unknown)}")
        if len(keys) != len(set(keys)):
            raise ValueError("duplicate questionnaire answers")
        return self

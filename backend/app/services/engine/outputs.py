"""Engine outputs. Money is integer paise; other quantities are Decimals (serialised as
strings) so nothing passes through a float outside the Monte Carlo simulation."""

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict


class Out(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class TraceRequirement(Out):
    id: str
    code: str
    text: str
    clause_ref: str | None
    page: int | None


class TraceComponent(Out):
    id: str
    catalog_key: str
    name: str
    size: str
    complexity: str
    quantity: int


class TraceAnswer(Out):
    """A questionnaire driver used by the line, with where its value came from."""

    key: str
    value: object
    source: Literal["user", "default"]
    requirement_ids: list[str]


class TraceRate(Out):
    key: str
    kind: str
    unit: str
    amount: Decimal
    currency: str
    rate_card_version: str
    source: str
    source_url: str | None


class TraceParameter(Out):
    path: str
    value: object
    parameter_set_version: str
    source: str


class TraceStep(Out):
    label: str
    expression: str
    value: Decimal


class SpreadFactor(Out):
    name: str
    down: Decimal
    up: Decimal


class Spread(Out):
    down: Decimal
    up: Decimal
    factors: list[SpreadFactor]


class LineTrace(Out):
    """The full chain for one number: clause + page -> requirement -> component -> drivers ->
    rate-card entries -> formula -> value (rule 2)."""

    requirements: list[TraceRequirement]
    component: TraceComponent | None
    drivers: list[TraceAnswer]
    rate_items: list[TraceRate]
    parameters: list[TraceParameter]
    formula_id: str
    formula: str
    steps: list[TraceStep]
    spread: Spread


class CostLineOut(Out):
    line_key: str
    stage: str
    bucket: str
    year: int  # 0 = build / one-off; 1..N = O&M year
    label: str
    component_instance_id: str | None
    formula_id: str
    inputs: dict[str, object]
    low_paise: int
    likely_paise: int
    high_paise: int
    requirement_ids: list[str]
    uncertainty_group: str
    derived: bool  # commercial line computed from other lines (contingency, margin, GST...)
    gst_percent: Decimal
    role_pd: dict[str, Decimal]  # person-days by role, for the manpower view
    trace: LineTrace


class Totals(Out):
    likely_paise: int
    low_sum_paise: int
    high_sum_paise: int
    p10_paise: int
    p50_paise: int
    p90_paise: int


class GroupTotal(Out):
    key: str
    name: str
    likely_paise: int
    low_paise: int
    high_paise: int


class Timeline(Out):
    build_effort_pd: Decimal
    build_effort_person_months: Decimal
    max_team: Decimal
    natural_duration_months: Decimal
    deadline_months: Decimal | None
    delivery_duration_months: Decimal
    programme_duration_months: Decimal
    compression_ratio: Decimal | None
    compression_multiplier: Decimal
    size_band: str
    status: Literal["natural", "compressed", "extended", "not_feasible"]


class ManpowerRow(Out):
    role: str
    stage: str
    year: int
    person_days: Decimal
    person_months: Decimal
    average_fte: Decimal


class RangeDriver(Out):
    bucket: str
    name: str
    variance_share: Decimal


class ConfidenceOut(Out):
    label: Literal["high", "medium", "low"]
    score: Decimal
    clarity_component: Decimal
    template_component: Decimal
    freshness_component: Decimal
    rate_card_age_days: int


class Calibration(Out):
    status: Literal["calibrated", "uncalibrated"]
    placeholder_refs: list[str]
    # Shared model-error spread applied in the simulation (from back-testing), if any.
    model_spread: SpreadFactor | None = None


class AssumptionOut(Out):
    key: str
    text: str
    value: object
    overridden: bool


class SanityCheck(Out):
    key: str
    status: Literal["ok", "flag"]
    message: str


class PhaseSuggestion(Out):
    phase: int
    component_instance_ids: list[str]
    build_effort_pd: Decimal
    natural_duration_months: Decimal


class Infeasibility(Out):
    message: str
    minimum_feasible_months: Decimal
    phases: list[PhaseSuggestion]


class ClientPaidNoteOut(Out):
    """A cost the client pays a third party directly, described by its published rate."""

    key: str
    label: str
    text: str
    rates: list[TraceRate]


class EstimateResult(Out):
    engine_version: str
    feasible: bool
    infeasibility: Infeasibility | None
    seed: int
    monte_carlo_runs: int
    versions: dict[str, str]
    lines: list[CostLineOut]
    totals: Totals | None
    by_stage: list[GroupTotal]
    by_bucket: list[GroupTotal]
    by_year: list[GroupTotal]
    timeline: Timeline
    manpower: list[ManpowerRow]
    top_drivers: list[RangeDriver]
    top_drivers_text: str
    confidence: ConfidenceOut
    calibration: Calibration
    assumptions: list[AssumptionOut]
    sanity_checks: list[SanityCheck]
    # Not part of the quote: costs the client pays directly (e.g. hosting they provide).
    client_paid: list[CostLineOut] = []
    client_paid_notes: list[ClientPaidNoteOut] = []

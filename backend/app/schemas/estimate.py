"""API schemas for estimates, cost lines, traces and scenarios."""

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field

from app.services.engine.outputs import (
    AssumptionOut,
    Calibration,
    ConfidenceOut,
    GroupTotal,
    Infeasibility,
    LineTrace,
    ManpowerRow,
    RangeDriver,
    SanityCheck,
    Timeline,
    Totals,
)
from app.services.engine.scenarios import Scenario, ScenarioResult


class EstimateCreate(BaseModel):
    seed: int | None = Field(default=None, ge=0)
    rate_card_version: str | None = None
    parameter_set_version: str | None = None
    catalog_version: str | None = None  # None = the newest catalog
    as_of_date: date | None = None
    monte_carlo_runs: int | None = Field(default=None, ge=100, le=100_000)


class EstimateSummary(BaseModel):
    id: str
    currency: str  # all *_paise amounts are minor units of this currency
    project_id: str
    version: int
    created_at: datetime
    rate_card_version: str
    parameter_set_version: str
    seed: int
    feasible: bool
    likely_paise: int | None
    p10_paise: int | None
    p50_paise: int | None
    p90_paise: int | None
    confidence: str
    calibration_status: str
    parent_estimate_id: str | None


class CostLineOut(BaseModel):
    id: str
    line_key: str
    stage: str
    bucket: str
    year: int
    label: str
    component_instance_id: str | None
    formula_id: str
    low_paise: int | None
    likely_paise: int | None
    high_paise: int | None
    requirement_ids: list[str]
    derived: bool
    redacted: bool = False


class EstimateOut(EstimateSummary):
    engine_version: str
    catalog_version: str
    taxonomy_version: str
    as_of_date: date
    frozen: bool
    margin_visible: bool
    totals: Totals | None
    infeasibility: Infeasibility | None
    timeline: Timeline
    confidence_detail: ConfidenceOut
    calibration: Calibration
    by_stage: list[GroupTotal]
    by_bucket: list[GroupTotal]
    by_year: list[GroupTotal]
    manpower: list[ManpowerRow]
    top_drivers: list[RangeDriver]
    top_drivers_text: str
    sanity_checks: list[SanityCheck]
    assumptions: list[AssumptionOut]
    lines: list[CostLineOut]


class TraceOut(BaseModel):
    estimate_id: str
    line: CostLineOut
    inputs: dict[str, Any]
    gst_percent: str
    trace: LineTrace | None  # None when redacted


class ScenariosRequest(BaseModel):
    scenarios: list[Scenario] = Field(min_length=1, max_length=8)


class ScenariosOut(BaseModel):
    estimate_id: str
    results: list[ScenarioResult]

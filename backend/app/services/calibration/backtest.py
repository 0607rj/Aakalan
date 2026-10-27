"""Back-testing and calibration against real, published contract values.

For each benchmark project in `seeds/benchmarks/<country>.yaml`, the scope (mapped onto the
quick-estimate form) is priced by the normal engine and compared with the published value:

    published today = published value × (1 + escalation_labour)^(this year − award year)
    ratio = our most-likely price (P50, matched for tax) / published today

Each project is priced twice: with AI tools (as the app prices today) and without them. A
contract awarded before AI coding tools were common (`pre_ai_until`, or the project's own
`pre_ai` flag) is judged against our price without AI tools, a later one against our price
with them: published prices reflect how the work was delivered when it was priced. The judged
column is a fairer measurement, not a different price.

Round 3 scoring (OPEN_QUESTIONS 151): published prices were costed on people's time, mostly
before AI tools, so our price WITHOUT AI tools is scored against the published price (target
1.0x), and our price WITH AI tools against the published price times the expected AI saving
(`ai_price_target`, e.g. 0.75-0.80x: inside it counts as exact, outside is measured to the
nearer edge, like a published band). The quoted price sits between the two when only part of
the AI saving is passed on (`ai_passthrough`). Each column has its own P10-P90 coverage.

A published price band (e.g. a review site's 10k–50k band) counts as exact when our price falls
inside it; otherwise the ratio is taken against the nearer edge.

Two paths (OPEN_QUESTIONS 161). The PRODUCTION PATH prices a tender the way the app does: its
saved reading (tests/fixtures/readings, read by a stand-in model, not the production API call),
then the review form accepted as it pre-fills (`prefill.review_prefill`), then the engine with
the reading passed in. It covers only the tenders with a saved reading. The LEGACY path below
(`benchmark_request`) is not the production path: the app never prices this way. It prices the
scope hand-mapped in the benchmark file, at fixed levels, with fixed answers.

The price follows what is built, not who orders it. Projects are priced the way the app prices
them: features at the level of the project's size class, and the size factor from the feature
points. Calibration (`fit_points_curve`) fits one smooth build-effort factor, a × points^b, on
custom builds of every client type together, minimising the mean |log ratio| over the projects
marked `use: true`; leave-one-out errors (each project priced with a curve fitted without it)
give the honest accuracy figure. Client types are only reported, never priced. The result is
published as a new parameter-set version (never applied silently), and its accuracy is shown in
the app. All arithmetic on money is integer minor units; the search itself is ordinary
floating-point statistics on ratios.
"""

import math
from datetime import UTC, date, datetime
from decimal import Decimal
from itertools import pairwise
from pathlib import Path
from statistics import median, quantiles
from typing import Any, Literal

import yaml
from fastapi import HTTPException
from pydantic import BaseModel, Field, model_validator

from app.services.engine.core import calculate
from app.services.engine.reference import Calibration, ParameterSet, version_key
from app.services.extraction.tender import TenderExtraction
from app.services.quick.config import LevelKey, QuickConfig
from app.services.quick.prefill import review_prefill
from app.services.quick.service import (
    CustomFeature,
    QuickPlan,
    QuickRequest,
    fastest_deadline,
    plan_quick,
    plan_to_input,
)
from app.services.seeding.reference import ReferenceData

BACKTEST_SEED = 7
BACKTEST_RUNS = 200  # P50 is stable enough for ranking at this many runs
SUPPORT_YEAR_CHOICES = {0, 1, 2, 3, 5}
SIZES = ("small", "medium", "large")
# A benchmark's features are priced at the level that matches its size class.
LEVEL_BY_SIZE: dict[str, LevelKey] = {
    "small": "basic",
    "small_medium": "basic",
    "medium": "standard",
    "medium_large": "advanced",
    "large": "advanced",
}
# A benchmark's user scale (small / medium / large) as the form's number-of-users answer.
SCALE_BY_CLASS = {"small": "up_to_10k", "medium": "up_to_1l", "large": "over_10l"}
PERCENT = 100
AI_USE = "ai_use"  # the form's question for the team's AI tools
NO_AI = "none"


class BenchmarkModel(BaseModel):
    buyer: str = "government"
    size: str | None = None  # small / medium / large: how big and deep the work is
    build_type: str | None = None  # custom / ready_product
    size_reason: str = ""  # why (EMD-implied budget, team and duration, or the scope)
    scale: str
    om_years: int = Field(ge=0)
    deadline_months: int | None = None
    features: list[str] = []
    # how many modules of its level a feature is (round 3 scope capture; unset = 1)
    feature_units: dict[str, int] = {}
    # each feature's level when the scope was measured (a reading); unset = the size class's
    feature_levels: dict[str, LevelKey] = {}
    custom_features: list[CustomFeature] = []
    hosting_included: bool = False
    helpdesk_included: bool = False
    # people the contract places at the client's office through support, as its tender states
    # (round 3 reading, pages in `reading.not_build`); priced as the form's onsite_staff answer
    onsite_staff: int | None = Field(default=None, ge=1)


class ReadModule(BaseModel):
    """One module a tender asks to be built, counted from the document (round 3)."""

    name: str
    feature_key: str  # a quick-config feature, or "custom"
    custom_type: str | None = None  # custom_feature_types key when feature_key is "custom"
    stories: int = Field(ge=0)
    level: LevelKey
    units: int = Field(default=1, ge=1)
    pages: str  # file and pages in the tender, to check the count
    confidence: str = ""


class Reading(BaseModel):
    """How a benchmark's scope was measured from its tender (round 3): who read it, the modules
    with their user stories and pages, and what the contract includes besides building
    software (flags only, never priced from here)."""

    reader: str
    files: list[str] = []
    modules: list[ReadModule]
    not_build: list[dict[str, str]] = []
    ready_product: bool = False
    notes: str = ""


ExcludeRule = Literal[
    "staffing", "subscription", "open_ended", "not_a_new_build", "unfinished", "unreliable_price"
]


class Benchmark(BaseModel):
    id: str
    title: str
    buyer: str = ""
    award_year: int
    value_minor: int = Field(gt=0)
    value_high_minor: int | None = None  # set when only a price band is published
    value_includes_tax: bool | None = None
    value_note: str = ""
    source_url: str
    confidence: str
    use: bool
    reason: str = ""
    # why it is left out: one of the written rules at the top of the benchmark file
    exclude_rule: ExcludeRule | None = None
    # Whether the contract was priced before AI coding tools were common; None = by award year
    # (BenchmarkSet.pre_ai_until).
    pre_ai: bool | None = None
    model: BenchmarkModel
    reading: Reading | None = None  # the scope measured from the tender (round 3)

    @model_validator(mode="after")
    def _left_out_by_a_rule(self) -> "Benchmark":
        """A project out of the back-test names the written rule and its reason (round 3)."""
        if not self.use and (self.exclude_rule is None or not self.reason):
            raise ValueError(f"{self.id}: left out without an exclude_rule and a reason")
        if self.use and self.exclude_rule is not None:
            raise ValueError(f"{self.id}: used, yet has an exclude_rule")
        return self


class PriceTarget(BaseModel):
    """Where our price with AI tools should sit, as a share of the published price."""

    low: Decimal = Field(gt=0)
    high: Decimal = Field(gt=0)
    source: str


class BenchmarkSet(BaseModel):
    country: str
    currency: str
    tax_included_when_unknown: bool = True
    # How much AI tooling vendors used in the year a contract was priced (older = none).
    ai_adoption_by_year: dict[int, str] = {}
    # Contracts awarded up to this year are judged against our price without AI tools.
    pre_ai_until: int | None = None
    # Our price with AI tools is scored against published × this band (round 3 scoring).
    ai_price_target: PriceTarget | None = None
    projects: list[Benchmark]

    def ai_level(self, year: int) -> str:
        known = [y for y in self.ai_adoption_by_year if y <= year]
        return self.ai_adoption_by_year[max(known)] if known else "none"

    def is_pre_ai(self, b: Benchmark) -> bool:
        if b.pre_ai is not None:
            return b.pre_ai
        return self.pre_ai_until is not None and b.award_year <= self.pre_ai_until


GOVERNMENT = "government"
COMMERCIAL = ("private", "small_business")
SEGMENTS = {
    GOVERNMENT: (GOVERNMENT,),
    "commercial": COMMERCIAL,
    "private": ("private",),
    "small_business": ("small_business",),
}


class BacktestRow(BaseModel):
    id: str
    title: str
    use: bool
    buyer: str
    published_minor: int  # in today's money (low edge of a band)
    published_high_minor: int | None  # high edge of a band, today's money
    estimate_minor: int | None
    estimate_low_minor: int | None = None  # our P10
    estimate_high_minor: int | None = None  # our P90
    inside_range: bool | None = None  # the published price (or band) meets our P10-P90 range
    ratio: float | None  # estimate / published
    error_percent: float | None
    size: str | None = None  # the size class set by hand from the scope text
    derived_size: str | None = None  # the size the app gives the scope (feature points)
    award_year: int | None = None
    band: bool = False  # published as a price band (inside it counts as exact)
    # Whether the published value includes GST (our price is matched to it), and whether the
    # source says so (False: assumed by tax_included_when_unknown). GST moves the ratio ~18%.
    gst_inclusive: bool = True
    gst_stated: bool = False
    # Both prices (P50, matched for tax) and their ratios; `estimate_minor` / `ratio` above are
    # the judged one: without AI tools for a contract priced before them (`pre_ai`).
    pre_ai: bool = False
    estimate_with_ai_minor: int | None = None
    estimate_pre_ai_minor: int | None = None
    ratio_with_ai: float | None = None
    ratio_pre_ai: float | None = None
    # Round 3 scoring: with AI tools against published × ai_price_target (inside counts as
    # exact), and each column's P10-P90 against its own target (the published price, or the
    # published price × the target band).
    ratio_ai_target: float | None = None
    inside_range_pre_ai: bool | None = None
    inside_range_ai_target: bool | None = None
    # production path: the stated deadline cannot be met, so it is priced at the fastest
    infeasible_deadline: int | None = None


class SegmentMetrics(BaseModel):
    """How one group of projects did. bias = exp(median log(ours / published)): above 1 we
    price higher than the published contracts. band_hits = projects counted exact only because
    our price fell inside a published band (they flatter the error and the bias)."""

    segment: str
    projects: int
    median_abs_error_percent: float
    bias: float
    within_25_percent: int
    inside_range: int  # published price meets our P10-P90
    band_hits: int


def segment_metrics(rows: list[BacktestRow], key: str) -> list[SegmentMetrics]:
    """Metrics per value of `key` ("size", "derived_size", "buyer", or "all"), used rows only."""
    used = [r for r in rows if r.use and r.ratio]
    groups: dict[str, list[BacktestRow]] = {}
    for r in used:
        groups.setdefault("all" if key == "all" else str(getattr(r, key)), []).append(r)
    out = []
    for name, group in sorted(groups.items()):
        errors = [abs(r.error_percent or 0) for r in group]
        out.append(
            SegmentMetrics(
                segment=name,
                projects=len(group),
                median_abs_error_percent=round(median(errors), 1),
                bias=round(math.exp(median(math.log(r.ratio or 1) for r in group)), 3),
                within_25_percent=sum(1 for e in errors if e <= 25),
                inside_range=sum(1 for r in group if r.inside_range),
                band_hits=sum(1 for r in group if r.band and r.ratio == 1.0),
            )
        )
    return out


BacktestPath = Literal["production", "legacy"]


class BacktestReport(BaseModel):
    country: str
    # production: reading -> review form -> engine (saved readings only); legacy: the benchmark
    # file's hand-mapped scope, a path the app never uses
    path: BacktestPath = "legacy"
    effort_multiplier: Decimal
    run_multiplier: Decimal
    projects_used: int
    median_ratio: float | None
    median_abs_error_percent: float | None
    within_25_percent: int
    inside_range: int = 0  # projects whose published price falls inside our P10-P90 range
    rows: list[BacktestRow]
    segments: dict[str, list[SegmentMetrics]] = {}  # by size, derived_size, buyer (judged)
    # the same on one column for every project: with AI tools, or without them
    segments_with_ai: dict[str, list[SegmentMetrics]] = {}
    segments_pre_ai: dict[str, list[SegmentMetrics]] = {}
    # round 3 scoring: with AI tools against published × ai_price_target
    segments_ai_target: dict[str, list[SegmentMetrics]] = {}
    ai_price_target: PriceTarget | None = None


def load_benchmarks(path: Path) -> BenchmarkSet:
    return BenchmarkSet.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))


def with_dials(
    params: ParameterSet,
    effort: Decimal,
    run: Decimal,
    factors: dict[str, Decimal] | None = None,
    size_factors: dict[str, Decimal] | None = None,
    answer_factors: dict[str, dict[str, Decimal]] | None = None,
) -> ParameterSet:
    """The parameter set with the given global dials and (optionally) build-effort factors for
    buyer segments, e.g. {"private": 0.5}, and for project sizes, e.g. {"small": 0.1} (support
    effort follows build effort already, so it gets no separate factor)."""
    base = params.calibration or Calibration(source="backtest")
    update: dict[str, Any] = {"effort_multiplier": effort, "run_multiplier": run}
    if factors:
        update["segment_effort_multiplier"] = {**base.segment_effort_multiplier, **factors}
    if size_factors:
        update["size_effort_multiplier"] = {**base.size_effort_multiplier, **size_factors}
    if answer_factors:
        merged = {k: dict(v) for k, v in base.answer_effort_multiplier.items()}
        for key, by_value in answer_factors.items():
            merged[key] = {**merged.get(key, {}), **by_value}
        update["answer_effort_multiplier"] = merged
    return params.model_copy(update={"calibration": base.model_copy(update=update)})


def today_value(minor: int, award_year: int, this_year: int, escalation: Decimal) -> int:
    """published × (1 + escalation)^(this_year − award_year), rounded to whole minor units."""
    years = max(0, this_year - award_year)
    return int((Decimal(minor) * (1 + escalation) ** years).to_integral_value())


def overlaps(ours: tuple[int, int, int], low: int, high: int | None) -> bool:
    """Our P10-P90 meets the target (a price, or a band)."""
    return ours[0] <= (high or low) and low <= ours[2]


def scaled(value: int, factor: Decimal) -> int:
    """value × factor, rounded to whole minor units."""
    return int((Decimal(value) * factor).to_integral_value())


def band_ratio(ours: int, low: int, high: int | None) -> float:
    """ours / published; inside a band counts as exact, outside is measured to the nearer edge."""
    if high is None:
        return ours / low
    if low <= ours <= high:
        return 1.0
    return ours / (low if ours < low else high)


def benchmark_request(
    cfg: QuickConfig, b: Benchmark, region: str, ai_level: str = "medium"
) -> QuickRequest:
    """The benchmark scope as the app's form: features at the level matching the project's
    size class, the AI use of the award year, and the extras a government contract above
    small size includes (an independent security audit, formal reports and review meetings)
    asked for explicitly."""
    m = b.model
    size = m.size or "medium"
    choices: dict[str, str | int] = {
        "scale": SCALE_BY_CLASS[m.scale],
        "ai_use": ai_level,
        **({"build_type": m.build_type} if m.build_type else {}),
        "hosting": "aws" if m.hosting_included else "existing",
        "helpdesk_scope": "yes" if m.helpdesk_included else "no",
    }
    if m.buyer == GOVERNMENT and size != "small":
        choices["security_audit"] = "yes"
        choices["reporting"] = "yes"
    if m.om_years in SUPPORT_YEAR_CHOICES:
        choices["support_years"] = m.om_years
    overrides: dict[str, int | float] = {"om_years": m.om_years}
    if m.deadline_months:
        overrides["deadline_months"] = m.deadline_months
    if m.onsite_staff:
        overrides["onsite_staff"] = m.onsite_staff
    return QuickRequest(
        name=b.title[:300],
        country=region,
        features=m.features,
        feature_levels={
            f: m.feature_levels.get(f, LEVEL_BY_SIZE[size])
            for f in dict.fromkeys(m.features)
            if cfg.feature(f).levels
        },
        feature_units=m.feature_units,
        custom_features=m.custom_features,
        choices=choices,
        overrides=overrides,
    )


def derived_size(cfg: QuickConfig, b: Benchmark, region: str) -> str:
    """The project size the app would give this scope (from its feature points)."""
    return plan_quick(cfg, benchmark_request(cfg, b, region), None, "benchmark").project_size


def estimate_range_for(
    cfg: QuickConfig,
    b: Benchmark,
    reference: dict[str, Any],
    tax_included: bool,
    ai_level: str = "medium",
    *,
    pin_size: bool = True,
    as_of: date | None = None,
) -> tuple[int, int, int] | None:
    """Our (P10, P50, P90) for the benchmark scope (`benchmark_request`), with or without tax
    to match the published value. `pin_size` prices it at its own size class instead of the
    size the app would derive from the feature points."""
    req = benchmark_request(cfg, b, reference["rate_card"].region, ai_level)
    size = b.model.size or "medium"
    plan = plan_quick(cfg, req, None, "benchmark", project_size=size if pin_size else None)
    return priced_range(plan, b.title, reference, tax_included, as_of)


def priced_range(
    plan: QuickPlan,
    title: str,
    reference: dict[str, Any],
    tax_included: bool,
    as_of: date | None,
) -> tuple[int, int, int] | None:
    """The plan's (P10, P50, P90) at the back-test's seed and runs, with or without tax to
    match the published value (None: the stated deadline cannot be met)."""
    inp = plan_to_input(
        plan,
        title[:300],
        reference,
        as_of or datetime.now(UTC).date(),
        BACKTEST_SEED,
        BACKTEST_RUNS,
    )
    result = calculate(inp)
    if result.totals is None:
        return None
    t = result.totals
    if tax_included:
        return t.p10_paise, t.p50_paise, t.p90_paise
    tax = sum(ln.likely_paise for ln in result.lines if ln.bucket == "commercial.gst")
    share = Decimal(t.likely_paise - tax) / t.likely_paise if t.likely_paise else Decimal(1)
    return tuple(
        int((Decimal(v) * share).to_integral_value())
        for v in (t.p10_paise, t.p50_paise, t.p90_paise)
    )  # type: ignore[return-value]


def estimate_for(
    cfg: QuickConfig,
    b: Benchmark,
    reference: dict[str, Any],
    tax_included: bool,
    ai_level: str = "medium",
    *,
    pin_size: bool = True,
) -> int | None:
    """Our P50 for the benchmark scope (see `estimate_range_for`)."""
    found = estimate_range_for(cfg, b, reference, tax_included, ai_level, pin_size=pin_size)
    return found[1] if found else None


def backtest(
    cfg: QuickConfig,
    bench: BenchmarkSet,
    reference: dict[str, Any],
    effort: Decimal,
    run: Decimal,
    *,
    used_only: bool = False,
    segment: str | None = None,
    factors: dict[str, Decimal] | None = None,
    size: str | None = None,
    size_factors: dict[str, Decimal] | None = None,
    build_type: str | None = None,
    answer_factors: dict[str, dict[str, Decimal]] | None = None,
    pin_size: bool = False,
    as_of: date | None = None,
) -> BacktestReport:
    """Price every benchmark (or one segment: government / commercial / private /
    small_business, and/or one project size) and compare, priced the way the app prices
    (size from the feature points; `pin_size` prices each at its own size class instead).
    `factors` / `size_factors` override the parameter set's segment / size factors."""
    params: ParameterSet = reference["parameters"]
    ref = {
        **reference,
        "parameters": with_dials(params, effort, run, factors, size_factors, answer_factors),
        "clarity": cfg.requirement_clarity,
    }
    escalation = params.escalation.labour
    as_of = as_of or datetime.now(UTC).date()  # pin it for a reproducible report
    with_ai_level = str(cfg.questions[AI_USE].default)  # how the app prices today
    rows = []
    for b in bench.projects:
        if used_only and not b.use:
            continue
        if segment is not None and b.model.buyer not in SEGMENTS[segment]:
            continue
        if size is not None and b.model.size != size:
            continue
        if build_type is not None and (b.model.build_type or "custom") != build_type:
            continue
        tax_included = gst_matched(bench, b)
        try:
            with_ai = estimate_range_for(
                cfg, b, ref, tax_included, with_ai_level, pin_size=pin_size, as_of=as_of
            )
            without_ai = estimate_range_for(
                cfg, b, ref, tax_included, NO_AI, pin_size=pin_size, as_of=as_of
            )
            sized: str | None = derived_size(cfg, b, ref["rate_card"].region)
        except HTTPException:  # scope too thin to model (e.g. no features known)
            with_ai, without_ai, sized = None, None, None
        rows.append(scored_row(bench, b, with_ai, without_ai, sized, as_of, escalation))
    return report_of(bench, effort, run, rows, "legacy")


def gst_matched(bench: BenchmarkSet, b: Benchmark) -> bool:
    """Whether the published value includes GST (as stated, else the file's assumption)."""
    if b.value_includes_tax is not None:
        return b.value_includes_tax
    return bench.tax_included_when_unknown


def scored_row(
    bench: BenchmarkSet,
    b: Benchmark,
    with_ai: tuple[int, int, int] | None,
    without_ai: tuple[int, int, int] | None,
    sized: str | None,
    as_of: date,
    escalation: Decimal,
    infeasible_deadline: int | None = None,
) -> BacktestRow:
    """One project's prices against its published value in today's money."""
    pre_ai = bench.is_pre_ai(b)
    found = without_ai if pre_ai else with_ai
    ours = found[1] if found else None
    low = today_value(b.value_minor, b.award_year, as_of.year, escalation)
    high = (
        today_value(b.value_high_minor, b.award_year, as_of.year, escalation)
        if b.value_high_minor
        else None
    )
    ratio = band_ratio(ours, low, high) if ours else None
    ratio_with = band_ratio(with_ai[1], low, high) if with_ai else None
    ratio_pre = band_ratio(without_ai[1], low, high) if without_ai else None
    # inside the range: our P10-P90 overlaps the published price (or its band)
    inside = overlaps(found, low, high) if found else None
    # round 3: with AI tools against published × the expected AI saving (a band)
    target = bench.ai_price_target
    t_low = scaled(low, target.low) if target else None
    t_high = scaled(high or low, target.high) if target else None
    ratio_target = band_ratio(with_ai[1], t_low, t_high) if with_ai and t_low else None
    return BacktestRow(
        id=b.id,
        title=b.title,
        use=b.use,
        buyer=b.model.buyer,
        published_minor=low,
        published_high_minor=high,
        estimate_minor=ours,
        estimate_low_minor=found[0] if found else None,
        estimate_high_minor=found[2] if found else None,
        inside_range=inside,
        ratio=round(ratio, 3) if ratio else None,
        error_percent=round((ratio - 1) * PERCENT, 1) if ratio else None,
        size=b.model.size,
        derived_size=sized,
        award_year=b.award_year,
        band=b.value_high_minor is not None,
        gst_inclusive=gst_matched(bench, b),
        gst_stated=b.value_includes_tax is not None,
        pre_ai=pre_ai,
        estimate_with_ai_minor=with_ai[1] if with_ai else None,
        estimate_pre_ai_minor=without_ai[1] if without_ai else None,
        ratio_with_ai=round(ratio_with, 3) if ratio_with else None,
        ratio_pre_ai=round(ratio_pre, 3) if ratio_pre else None,
        ratio_ai_target=round(ratio_target, 3) if ratio_target else None,
        inside_range_pre_ai=overlaps(without_ai, low, high) if without_ai else None,
        inside_range_ai_target=overlaps(with_ai, t_low, t_high) if with_ai and t_low else None,
        infeasible_deadline=infeasible_deadline,
    )


def report_of(
    bench: BenchmarkSet,
    effort: Decimal,
    run: Decimal,
    rows: list[BacktestRow],
    path: BacktestPath,
) -> BacktestReport:
    """The rows with their overall and per-segment figures (used projects only)."""
    used = [r for r in rows if r.use and r.ratio]
    errors = [abs(r.error_percent or 0) for r in used]
    return BacktestReport(
        country=bench.country,
        path=path,
        effort_multiplier=effort,
        run_multiplier=run,
        projects_used=len(used),
        median_ratio=round(median(r.ratio for r in used if r.ratio), 3) if used else None,
        median_abs_error_percent=round(median(errors), 1) if errors else None,
        within_25_percent=sum(1 for e in errors if e <= 25),
        inside_range=sum(1 for r in used if r.inside_range),
        rows=rows,
        segments={k: segment_metrics(rows, k) for k in KEYS},
        segments_with_ai={k: segment_metrics(on_column(rows, "with_ai"), k) for k in KEYS},
        segments_pre_ai={k: segment_metrics(on_column(rows, "pre_ai"), k) for k in KEYS},
        segments_ai_target=(
            {k: segment_metrics(on_column(rows, "ai_target"), k) for k in KEYS}
            if bench.ai_price_target
            else {}
        ),
        ai_price_target=bench.ai_price_target,
    )


# ---------------------------------------------------------------- production path


class SavedReading(BaseModel):
    """A tender's reading saved for the production-path back-test (tests/fixtures/readings):
    who read it and when, the files read, and the merged reading the app would store."""

    benchmark_id: str
    reader_model: str  # e.g. a stand-in model, not the production API call
    read_on: date
    code_path: str
    files_read: list[str] = Field(min_length=1)  # the first is uploaded as the RFP
    files_not_read: list[dict[str, str]] = []
    extraction: TenderExtraction


def load_readings(folder: Path) -> dict[str, SavedReading]:
    """The saved readings in `folder`, by benchmark id."""
    out: dict[str, SavedReading] = {}
    for f in sorted(folder.glob("*.json")):
        r = SavedReading.model_validate_json(f.read_text(encoding="utf-8"))
        out[r.benchmark_id] = r
    return out


def reading_request(
    cfg: QuickConfig, reading: SavedReading, country: str, ai_level: str
) -> QuickRequest:
    """What the review form sends for the reading when the user accepts everything, with the
    back-test's AI use (a company setting, not asked on the form)."""
    req = review_prefill(cfg, reading.extraction, country).request
    return req.model_copy(update={"choices": {**req.choices, AI_USE: ai_level}})


def reading_range_for(
    cfg: QuickConfig,
    reading: SavedReading,
    reference: dict[str, Any],
    tax_included: bool,
    ai_level: str,
    *,
    country: str,
    as_of: date | None = None,
) -> tuple[tuple[int, int, int] | None, str, int | None]:
    """Our (P10, P50, P90) for a tender priced as the app prices it: the review form's request
    for its reading, planned with the reading passed in (as POST /quick-estimates does), the
    project size it gets, and a stated deadline that could not be met (priced again at the
    fastest possible time, as the app does, OPEN_QUESTIONS 179)."""
    req = reading_request(cfg, reading, country, ai_level)
    extraction = reading.extraction.model_dump(mode="json")
    filename = reading.files_read[0]
    plan = plan_quick(cfg, req, extraction, filename)
    found = priced_range(plan, req.name, reference, tax_included, as_of)
    deadline = req.overrides.get("deadline_months")
    if found is not None or deadline is None:
        return found, plan.project_size, None
    inp = plan_to_input(
        plan,
        req.name[:300],
        reference,
        as_of or datetime.now(UTC).date(),
        BACKTEST_SEED,
        BACKTEST_RUNS,
    )
    fastest = fastest_deadline(inp)
    assert fastest is not None  # no price only for a deadline too short to build in
    over = {**req.overrides, "deadline_months": float(fastest)}
    plan = plan_quick(cfg, req.model_copy(update={"overrides": over}), extraction, filename)
    found = priced_range(plan, req.name, reference, tax_included, as_of)
    return found, plan.project_size, int(deadline)


def backtest_production(
    cfg: QuickConfig,
    bench: BenchmarkSet,
    reference: dict[str, Any],
    effort: Decimal,
    run: Decimal,
    readings: dict[str, SavedReading],
    *,
    as_of: date | None = None,
) -> BacktestReport:
    """The production-path back-test: every benchmark with a saved reading, priced as the app
    prices an uploaded tender whose review form is accepted as it pre-fills."""
    params: ParameterSet = reference["parameters"]
    ref = {
        **reference,
        "parameters": with_dials(params, effort, run),
        "clarity": cfg.requirement_clarity,
    }
    as_of = as_of or datetime.now(UTC).date()  # pin it for a reproducible report
    with_ai_level = str(cfg.questions[AI_USE].default)  # how the app prices today
    rows = []
    for b in bench.projects:
        reading = readings.get(b.id)
        if reading is None:
            continue
        tax_included = gst_matched(bench, b)
        with_ai, _, _ = reading_range_for(
            cfg, reading, ref, tax_included, with_ai_level, country=bench.country, as_of=as_of
        )
        without_ai, sized, dropped = reading_range_for(
            cfg, reading, ref, tax_included, NO_AI, country=bench.country, as_of=as_of
        )
        escalation = params.escalation.labour
        rows.append(scored_row(bench, b, with_ai, without_ai, sized, as_of, escalation, dropped))
    return report_of(bench, effort, run, rows, "production")


KEYS = ("all", "size", "derived_size", "buyer")


def on_column(rows: list[BacktestRow], column: str) -> list[BacktestRow]:
    """The rows judged on one column for every project: "with_ai", "pre_ai" (against the
    published price) or "ai_target" (with AI tools against published × ai_price_target), with
    that column's own P10-P90 coverage where it is measured ("with_ai" has none)."""
    out = []
    for r in rows:
        ratio: float | None = getattr(r, f"ratio_{column}")
        out.append(
            r.model_copy(
                update={
                    "ratio": ratio,
                    "error_percent": round((ratio - 1) * PERCENT, 1) if ratio else None,
                    "inside_range": getattr(r, f"inside_range_{column}", None),
                }
            )
        )
    return out


def reference_for(data: ReferenceData, country: str) -> dict[str, Any]:
    """Newest seed rate card and parameter set for the country (as the app would use)."""
    cards = [c for c in data.rate_cards if c.region == country and c.status == "active"]
    params = [p for p in data.parameter_sets if p.region == country and p.status == "active"]
    if not cards or not params:
        raise ValueError(f"No active rate card / parameter set for {country!r}")
    return {
        "taxonomy": data.taxonomy,
        "catalog": data.catalog,
        "rate_card": max(cards, key=lambda c: (c.effective_date, version_key(c.version))),
        "parameters": max(params, key=lambda p: (p.effective_date, version_key(p.version))),
        "clarity": None,
    }


class SizeStats(BaseModel):
    projects: int
    within_25_percent: int  # left out
    loo_median_abs_error_percent: float | None
    p25_actual_over_ours: float | None  # spread of the real prices around ours
    p75_actual_over_ours: float | None


class CurveFit(BaseModel):
    """One smooth build-effort factor by feature points, factor = a × points^b, priced the way
    the app prices (size from the feature points), fitted on every client type together."""

    a: float
    b: float
    curve: list[tuple[int, Decimal]]  # (points, factor) samples for the parameter set
    projects: int
    median_abs_error_percent: float | None  # in-sample
    loo_median_abs_error_percent: float | None  # each project priced with a fit without it
    loo_within_25_percent: int
    by_size: dict[str, SizeStats]  # by the benchmark's own size class
    by_buyer: dict[str, float]  # median actual / ours, left out (client types only reported)


# size factors each project is priced at; prices in between are interpolated (log-linear)
CURVE_FACTORS = [
    Decimal(x)
    for x in ("0.05", "0.1", "0.2", "0.3", "0.45", "0.6", "0.8", "1.0", "1.3", "1.7", "2.2")
]
CURVE_A = [0.02 * 1.15**i for i in range(40)]  # a: 0.02 … about 4.6
CURVE_B = [x / 20 for x in range(-10, 31)]  # b: −0.5 … 1.5
CURVE_POINTS = [1, 2, 3, 4, 6, 8, 10, 12, 14, 16, 20, 25, 30, 40, 50, 60, 80]
TIERS = ("small", "small_medium", "medium", "medium_large", "large")


def fit_points_curve(cfg: QuickConfig, bench: BenchmarkSet, reference: dict[str, Any]) -> CurveFit:
    """Fit factor(points) = a × points^b on custom builds.

    Each project is priced (as the app would, size from its feature points) at a fixed ladder
    of size factors; its price at any factor is the log-linear interpolation between them, so
    the grid search over (a, b) needs no further pricing. Score: mean |log(ours / published)|,
    a published band counting as exact inside it. Leave-one-out refits without each project.
    """
    params: ParameterSet = reference["parameters"]
    cal = params.calibration or Calibration(source="backtest")
    flat = params.model_copy(
        update={"calibration": cal.model_copy(update={"size_points_curve": []})}
    )
    escalation = params.escalation.labour
    this_year = datetime.now(UTC).year
    region = reference["rate_card"].region
    used = [b for b in bench.projects if b.use and (b.model.build_type or "custom") == "custom"]
    ladders: dict[str, list[tuple[float, float]]] = {}
    published: dict[str, tuple[int, int | None]] = {}
    points: dict[str, int] = {}
    for b in used:
        points[b.id] = plan_quick(cfg, benchmark_request(cfg, b, region), None, "b").size_points
        published[b.id] = (
            today_value(b.value_minor, b.award_year, this_year, escalation),
            today_value(b.value_high_minor, b.award_year, this_year, escalation)
            if b.value_high_minor
            else None,
        )
        tax = (
            b.value_includes_tax
            if b.value_includes_tax is not None
            else bench.tax_included_when_unknown
        )
        ladder = []
        for f in CURVE_FACTORS:
            p = with_dials(
                flat,
                cal.effort_multiplier,
                cal.run_multiplier,
                size_factors=dict.fromkeys(TIERS, f),
            )
            ref = {**reference, "parameters": p, "clarity": cfg.requirement_clarity}
            try:
                ours = estimate_for(cfg, b, ref, tax, bench.ai_level(b.award_year), pin_size=False)
            except HTTPException:
                ours = None
            if ours:
                ladder.append((math.log(float(f)), math.log(ours)))
        if len(ladder) >= 2:
            ladders[b.id] = ladder
    lo_f, hi_f = float(CURVE_FACTORS[0]), float(CURVE_FACTORS[-1])

    def ratio(pid: str, a: float, b: float) -> float:
        f = min(max(a * points[pid] ** b, lo_f), hi_f)
        ladder, x = ladders[pid], math.log(f)
        for (x0, y0), (x1, y1) in pairwise(ladder):
            if x <= x1 or (x1, y1) == ladder[-1]:
                ours = math.exp(y0 + (x - x0) / (x1 - x0) * (y1 - y0))
                break
        low, high = published[pid]
        return band_ratio(round(ours), low, high)

    def fit(skip: str | None = None) -> tuple[float, float]:
        def score(ab: tuple[float, float]) -> float:
            logs = [abs(math.log(ratio(p, *ab))) for p in ladders if p != skip]
            return sum(logs) / len(logs)

        return min(((a, b) for a in CURVE_A for b in CURVE_B), key=score)

    a, power = fit()
    inside = [abs(ratio(p, a, power) - 1) * PERCENT for p in ladders]
    loo = {p: (ratio(p, *fit(skip=p)) - 1) * PERCENT for p in ladders}
    by_id = {x.id: x for x in used}
    by_size: dict[str, SizeStats] = {}
    for size in SIZES:
        ids = [p for p in loo if by_id[p].model.size == size]
        if not ids:
            continue
        spread = sorted(1 / (1 + loo[p] / PERCENT) for p in ids)
        q = quantiles(spread, n=4) if len(spread) > 1 else [spread[0]] * 3
        by_size[size] = SizeStats(
            projects=len(ids),
            within_25_percent=sum(1 for p in ids if abs(loo[p]) <= 25),
            loo_median_abs_error_percent=round(median(abs(loo[p]) for p in ids), 1),
            p25_actual_over_ours=round(q[0], 2),
            p75_actual_over_ours=round(q[2], 2),
        )
    by_buyer = {
        buyer: round(median(1 / (1 + loo[p] / PERCENT) for p in ids), 2)
        for buyer in sorted({x.model.buyer for x in used})
        if (ids := [p for p in loo if by_id[p].model.buyer == buyer])
    }
    errors = [abs(e) for e in loo.values()]
    return CurveFit(
        a=round(a, 4),
        b=power,
        curve=[(n, Decimal(str(round(a * n**power, 3)))) for n in CURVE_POINTS],
        projects=len(ladders),
        median_abs_error_percent=round(median(inside), 1) if inside else None,
        loo_median_abs_error_percent=round(median(errors), 1) if errors else None,
        loo_within_25_percent=sum(1 for e in errors if e <= 25),
        by_size=by_size,
        by_buyer=by_buyer,
    )


LAYER_ORDER = (
    "feature blocks",
    "standard blocks",
    "other build",  # tools, review of AI-written code
    "management",
    "launch",
    "running",
    "commercial",
)


def layer_shares(
    cfg: QuickConfig,
    bench: BenchmarkSet,
    reference: dict[str, Any],
    *,
    as_of: date | None = None,
) -> dict[str, dict[str, float]]:
    """How the planned cost (sum of line items) splits into layers, median share by hand-set
    size, priced as the app prices: feature blocks (components a feature or scope item asked
    for), standard blocks (asked for by none), management (programme stage), launch (go-live),
    running (run), commercial, and other build lines. A diagnostic of how size changes the
    mix, never a fit."""
    ref = {**reference, "clarity": cfg.requirement_clarity}
    shares: dict[str, dict[str, list[float]]] = {}
    for b in bench.projects:
        if not b.use:
            continue
        try:
            req = benchmark_request(cfg, b, ref["rate_card"].region, bench.ai_level(b.award_year))
            plan = plan_quick(cfg, req, None, "benchmark")
        except HTTPException:  # scope too thin to model
            continue
        inp = plan_to_input(
            plan,
            b.title[:300],
            ref,
            as_of or datetime.now(UTC).date(),
            BACKTEST_SEED,
            BACKTEST_RUNS,
        )
        asked = {c.id for c in inp.components if c.requirement_ids}
        layers = dict.fromkeys(LAYER_ORDER, 0)
        stage_layer = {
            "programme": "management",
            "go_live": "launch",
            "run": "running",
            "commercial": "commercial",
        }
        for line in calculate(inp).lines:
            if line.component_instance_id:
                key = "feature blocks" if line.component_instance_id in asked else "standard blocks"
            else:
                key = stage_layer.get(line.stage, "other build")
            layers[key] += line.likely_paise
        total = sum(layers.values())
        if total <= 0:
            continue
        group = shares.setdefault(b.model.size or "unknown", {k: [] for k in LAYER_ORDER})
        for key, value in layers.items():
            group[key].append(value / total)
    return {
        size: {k: round(median(v), 3) for k, v in by_layer.items() if v}
        for size, by_layer in shares.items()
    }

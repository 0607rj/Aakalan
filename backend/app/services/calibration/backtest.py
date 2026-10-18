"""Back-testing and calibration against real, published contract values.

For each benchmark project in `seeds/benchmarks/<country>.yaml`, the scope (mapped onto the
quick-estimate form) is priced by the normal engine and compared with the published value:

    published today = published value × (1 + escalation_labour)^(this year − award year)
    ratio = our most-likely price (P50, matched for tax) / published today

A published price band (e.g. a review site's 10k–50k band) counts as exact when our price falls
inside it; otherwise the ratio is taken against the nearer edge.

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
from datetime import UTC, datetime
from decimal import Decimal
from itertools import pairwise
from pathlib import Path
from statistics import median, quantiles
from typing import Any

import yaml
from fastapi import HTTPException
from pydantic import BaseModel, Field

from app.services.engine.core import calculate
from app.services.engine.reference import Calibration, ParameterSet, version_key
from app.services.quick.config import LevelKey, QuickConfig
from app.services.quick.service import CustomFeature, QuickRequest, plan_quick, plan_to_input
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


class BenchmarkModel(BaseModel):
    buyer: str = "government"
    size: str | None = None  # small / medium / large: how big and deep the work is
    build_type: str | None = None  # custom / ready_product
    size_reason: str = ""  # why (EMD-implied budget, team and duration, or the scope)
    scale: str
    om_years: int = Field(ge=0)
    deadline_months: int | None = None
    features: list[str] = []
    custom_features: list[CustomFeature] = []
    hosting_included: bool = False
    helpdesk_included: bool = False


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
    model: BenchmarkModel


class BenchmarkSet(BaseModel):
    country: str
    currency: str
    tax_included_when_unknown: bool = True
    # How much AI tooling vendors used in the year a contract was priced (older = none).
    ai_adoption_by_year: dict[int, str] = {}
    projects: list[Benchmark]

    def ai_level(self, year: int) -> str:
        known = [y for y in self.ai_adoption_by_year if y <= year]
        return self.ai_adoption_by_year[max(known)] if known else "none"


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


class BacktestReport(BaseModel):
    country: str
    effort_multiplier: Decimal
    run_multiplier: Decimal
    projects_used: int
    median_ratio: float | None
    median_abs_error_percent: float | None
    within_25_percent: int
    inside_range: int = 0  # projects whose published price falls inside our P10-P90 range
    rows: list[BacktestRow]


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
    return QuickRequest(
        name=b.title[:300],
        country=region,
        features=m.features,
        feature_levels={
            f: LEVEL_BY_SIZE[size] for f in dict.fromkeys(m.features) if cfg.feature(f).levels
        },
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
) -> tuple[int, int, int] | None:
    """Our (P10, P50, P90) for the benchmark scope (`benchmark_request`), with or without tax
    to match the published value. `pin_size` prices it at its own size class instead of the
    size the app would derive from the feature points."""
    req = benchmark_request(cfg, b, reference["rate_card"].region, ai_level)
    size = b.model.size or "medium"
    plan = plan_quick(cfg, req, None, "benchmark", project_size=size if pin_size else None)
    inp = plan_to_input(
        plan, b.title[:300], reference, datetime.now(UTC).date(), BACKTEST_SEED, BACKTEST_RUNS
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
    this_year = datetime.now(UTC).year
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
        tax_included = (
            b.value_includes_tax
            if b.value_includes_tax is not None
            else bench.tax_included_when_unknown
        )
        try:
            found = estimate_range_for(
                cfg, b, ref, tax_included, bench.ai_level(b.award_year), pin_size=pin_size
            )
        except HTTPException:  # scope too thin to model (e.g. no features known)
            found = None
        ours = found[1] if found else None
        low = today_value(b.value_minor, b.award_year, this_year, escalation)
        high = (
            today_value(b.value_high_minor, b.award_year, this_year, escalation)
            if b.value_high_minor
            else None
        )
        ratio = band_ratio(ours, low, high) if ours else None
        # inside the range: our P10-P90 overlaps the published price (or its band)
        inside = found[0] <= (high or low) and low <= found[2] if found else None
        rows.append(
            BacktestRow(
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
            )
        )
    used = [r for r in rows if r.use and r.ratio]
    errors = [abs(r.error_percent or 0) for r in used]
    return BacktestReport(
        country=bench.country,
        effort_multiplier=effort,
        run_multiplier=run,
        projects_used=len(used),
        median_ratio=round(median(r.ratio for r in used if r.ratio), 3) if used else None,
        median_abs_error_percent=round(median(errors), 1) if errors else None,
        within_25_percent=sum(1 for e in errors if e <= 25),
        inside_range=sum(1 for r in used if r.inside_range),
        rows=rows,
    )


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

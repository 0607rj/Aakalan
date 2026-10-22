"""Commercial layer (brief 7.5): EMD lock-up, exit management, contingency, working capital,
PBG charges, penalty / LD reserve, margin and GST.

Contingency, working capital, PBG, penalty reserve, margin and GST are *derived* lines: linear
functions of base-line subtotals. `derived_amounts` is written once and evaluated both on
Decimals (the likely / low / high values) and on NumPy arrays (each Monte Carlo run), so the
simulation applies exactly the same formulas as the deterministic estimate.
"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass, fields, replace
from decimal import Decimal
from itertools import pairwise
from typing import Any

from app.services.engine import spreads
from app.services.engine.context import LineBuilder, PricingContext
from app.services.engine.money import ONE, ZERO, dsum, interpolate, paise_to_rupees
from app.services.engine.outputs import CostLineOut, Timeline
from app.services.engine.timeline import size_band

DERIVED_ORDER = ("contingency", "working_capital", "pbg", "penalty_reserve", "margin", "gst")
FORMULA_IDS = {key: f"commercial.{key}.v1" for key in DERIVED_ORDER} | {
    "working_capital": "commercial.working_capital.v2"
}


@dataclass(frozen=True)
class BaseSums:
    """Subtotals of base (non-derived) lines. Fields are Decimal rupees or NumPy arrays."""

    total: Any
    build: Any  # year-0 lines outside the commercial stage
    run: Any  # O&M-year lines
    by_gst_rate: dict[Decimal, Any]


@dataclass(frozen=True)
class Factors:
    contingency: Any
    working_capital: Any
    pbg: Any
    ld_build: Any
    penalty_run: Any
    margin: Any
    gst_contingency: Any
    gst_working_capital: Any
    gst_pbg: Any
    gst_penalty_reserve: Any
    gst_margin: Any

    def map(self, fn: Callable[[Decimal], Any]) -> "Factors":
        return replace(self, **{f.name: fn(getattr(self, f.name)) for f in fields(self)})


def derived_amounts(b: BaseSums, f: Factors, rate: Callable[[Decimal], Any]) -> dict[str, Any]:
    """C   = contingency × total
    WC  = working_capital_factor × build
    PBG = pbg_factor × (total + C)
    LD  = ld_build × build + penalty_run × run
    M   = margin × (total + C + WC + PBG + LD)
    GST = Σ_rate rate × base_at_rate + Σ_derived gst_derived × derived
    """
    c = f.contingency * b.total
    wc = f.working_capital * b.build
    pbg = f.pbg * (b.total + c)
    ld = f.ld_build * b.build + f.penalty_run * b.run
    m = f.margin * (b.total + c + wc + pbg + ld)
    gst = sum((rate(r) * v for r, v in sorted(b.by_gst_rate.items())), rate(ZERO) * b.total)
    gst = (
        gst
        + f.gst_contingency * c
        + f.gst_working_capital * wc
        + f.gst_pbg * pbg
        + f.gst_penalty_reserve * ld
        + f.gst_margin * m
    )
    return {
        "contingency": c,
        "working_capital": wc,
        "pbg": pbg,
        "penalty_reserve": ld,
        "margin": m,
        "gst": gst,
    }


def base_sums(lines: Sequence[CostLineOut], attr: str) -> BaseSums:
    """Decimal-rupee subtotals of base lines, using `attr` (low/likely/high_paise)."""
    total = build = run = ZERO
    by_rate: dict[Decimal, Decimal] = {}
    for line in lines:
        if line.derived:
            continue
        v = paise_to_rupees(getattr(line, attr))
        total += v
        if line.year == 0 and line.stage != "commercial":
            build += v
        elif line.year > 0:
            run += v
        by_rate[line.gst_percent] = by_rate.get(line.gst_percent, ZERO) + v
    return BaseSums(total, build, run, by_rate)


# --- base commercial lines -------------------------------------------------------------------


def base_commercial_lines(ctx: PricingContext, timeline: Timeline) -> list[CostLineOut]:
    lines: list[CostLineOut] = []
    t = ctx.builder(
        line_key="commercial.emd/lockup",
        stage="commercial",
        bucket="commercial.emd",
        year=0,
        label="EMD lock-up (cost of capital)",
        formula_id="commercial.emd.v1",
    )
    emd_paise: int = t.driver("emd_paise")
    if emd_paise:
        lock: Decimal = t.driver("emd_lock_months")
        coc: Decimal = t.param("commercial", "cost_of_capital")
        emd = paise_to_rupees(emd_paise)
        months = ctx.months_per_year()
        cost = t.step(
            "EMD lock-up cost", f"₹{emd} × {coc} × {lock} / {months}", emd * coc * lock / months
        )
        lines.append(t.finish(cost))

    if ctx.q.governance_overheads:  # exit management is a government contract clause
        t = ctx.builder(
            line_key="commercial.exit_management/exit",
            stage="commercial",
            bucket="commercial.exit_management",
            year=0,
            label="Exit management and handover",
            formula_id="commercial.exit.v1",
        )
        idx, _ = size_band(ctx, timeline.build_effort_pd)
        pd: Decimal = t.param("timeline", "size_bands", idx, "exit_management_pd")
        role: str = t.param("commercial", "exit_role")
        t.add_role_pd(role, pd)
        spreads.clarity(t, ctx.overall_clarity())
        lines.append(t.finish(pd * t.rate_local(role)))
    return lines


# --- derived lines ---------------------------------------------------------------------------


def working_capital_factor(t: LineBuilder, delivery_months: Decimal) -> Decimal:
    """∫ max(0, cost_share(τ) − receipts_share(τ)) dτ × cost_of_capital / months_per_year.

    Costs accrue evenly over delivery (cost_share = min(1, τ / delivery)); receipts step up at
    each payment-schedule milestone (+ payment delay). The integral is exact over
    piecewise-linear segments, so the factor moves continuously with the delivery duration.
    """
    schedule = t.driver("payment_schedule")
    delay: Decimal = t.param("commercial", "payment_delay_months")
    coc: Decimal = t.param("commercial", "cost_of_capital")
    payments = [
        (m.at_build_fraction * delivery_months + m.offset_months + delay, m.percent)
        for m in schedule
    ] or [(delivery_months + delay, ONE)]
    points = sorted({ZERO, delivery_months, *(at for at, _ in payments)})

    def gap(tau: Decimal, received: Decimal) -> Decimal:
        return min(ONE, tau / delivery_months) - received

    area = ZERO
    for a, b in pairwise(points):
        received = dsum(pct for at, pct in payments if at <= a)
        ga, gb = gap(a, received), gap(b, received)
        width = b - a
        if ga >= 0 and gb >= 0:
            area += (ga + gb) / 2 * width
        elif ga > 0 > gb:
            area += ga * ga / (ga - gb) * width / 2
        elif gb > 0 > ga:
            area += gb * gb / (gb - ga) * width / 2
    t.step("unfunded build-share months", "∫ max(0, cost_share − receipts) dτ", area)
    return t.step(
        "working-capital factor",
        f"{area:.4f} × {coc} / {ctx_months(t)}",
        area * coc / ctx_months(t),
    )


def ctx_months(t: LineBuilder) -> Decimal:
    return t.ctx.months_per_year()


def derived_lines(
    ctx: PricingContext, timeline: Timeline, base: Sequence[CostLineOut]
) -> tuple[list[CostLineOut], Factors]:
    builders: dict[str, LineBuilder] = {}
    names = {
        "contingency": "Contingency",
        "working_capital": "Working capital (milestone payments)",
        "pbg": "Performance bank guarantee charges",
        "penalty_reserve": "Penalty / LD reserve",
        "margin": "Margin",
        "gst": ctx.p.commercial.tax_label,
    }
    for key in DERIVED_ORDER:
        builders[key] = ctx.builder(
            line_key=f"commercial.{key}/total",
            stage="commercial",
            bucket=f"commercial.{key}",
            year=0,
            label=names[key],
            formula_id=FORMULA_IDS[key],
        )

    t = builders["contingency"]
    override: Decimal | None = t.driver("contingency_percent")
    if override is not None:
        contingency = override
    else:
        points = t.param("commercial", "contingency_at_clarity")
        clarity = ctx.overall_clarity()
        contingency = t.step(
            "contingency %",
            f"interpolate(contingency_at_clarity, clarity {clarity:.2f})",
            interpolate(points, clarity),
        )

    wc = working_capital_factor(builders["working_capital"], timeline.delivery_duration_months)

    t = builders["pbg"]
    pbg_pct: Decimal = t.driver("pbg_percent")
    validity: Decimal | None = t.driver("pbg_validity_months")
    if validity is None:
        t.driver("om_years")
        validity = t.step(
            "PBG validity months",
            "delivery months + om_years × months_per_year",
            timeline.delivery_duration_months + ctx.q.om_years * ctx.months_per_year(),
        )
    commission = t.rate_local(t.param("commercial", "pbg_rate_key"))
    pbg = t.step(
        "PBG factor",
        f"{pbg_pct} × {commission} × {validity} / {ctx.months_per_year()}",
        pbg_pct * commission * validity / ctx.months_per_year(),
    )

    t = builders["penalty_reserve"]
    # v19+: no reserve for penalties the contract does not have (no cited penalty clause)
    if ctx.p.commercial.penalty_needs_clause and not t.driver("penalty_clause"):
        t.param("commercial", "penalty_needs_clause")
        ld_build = penalty_run = t.step(
            "penalty reserve", "no penalty clause in the contract", ZERO
        )
    else:
        ld_build = t.param("commercial", "ld_reserve_build_percent")
        penalty_run = t.param("commercial", "penalty_reserve_run_percent", t.driver("support_sla"))

    margin: Decimal = builders["margin"].driver("margin_percent")

    gst_default = ctx.q.gst_percent
    g = builders["gst"]
    g.driver("gst_percent")
    if gst_default is None:
        gst_default = g.param("commercial", "gst_percent")

    def gst_of(bucket: str) -> Decimal:
        rate = ctx.inp.taxonomy.bucket(bucket).gst_percent
        return gst_default if rate is None else rate

    factors = Factors(
        contingency=contingency,
        working_capital=wc,
        pbg=pbg,
        ld_build=ld_build,
        penalty_run=penalty_run,
        margin=margin,
        gst_contingency=gst_of("commercial.contingency"),
        gst_working_capital=gst_of("commercial.working_capital"),
        gst_pbg=gst_of("commercial.pbg"),
        gst_penalty_reserve=gst_of("commercial.penalty_reserve"),
        gst_margin=gst_of("commercial.margin"),
    )

    def ident(rate: Decimal) -> Decimal:
        return rate

    points = {
        attr: derived_amounts(base_sums(base, attr), factors, ident)
        for attr in ("low_paise", "likely_paise", "high_paise")
    }
    likely_base = base_sums(base, "likely_paise")
    lines = []
    for key in DERIVED_ORDER:
        t = builders[key]
        t.step("base total", "Σ base lines (likely)", likely_base.total)
        t.step("build base", "Σ year-0 base lines", likely_base.build)
        t.step("run base", "Σ O&M-year base lines", likely_base.run)
        t.add_input(**{f"factor_{f.name}": str(getattr(factors, f.name)) for f in fields(factors)})
        lines.append(
            t.finish_three_point(
                points["low_paise"][key],
                points["likely_paise"][key],
                points["high_paise"][key],
                gst_percent=ZERO if key == "gst" else gst_of(f"commercial.{key}"),
            )
        )
    return lines, factors

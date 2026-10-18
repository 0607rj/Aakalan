"""Engine entry point: `calculate(EstimateInput) -> EstimateResult`.

Deterministic: Decimal arithmetic in a fixed context, paise rounding at each line, and a
seeded Monte Carlo. Same input snapshot ⇒ byte-identical result (rule 3).
"""

from collections import defaultdict
from collections.abc import Callable, Iterable
from decimal import Decimal, localcontext
from typing import Literal

from app.services.engine.commercial import base_commercial_lines, derived_lines
from app.services.engine.components import ai_review_line, base_effort, component_line
from app.services.engine.context import PricingContext
from app.services.engine.golive_programme import golive_lines, programme_lines
from app.services.engine.inputs import EstimateInput
from app.services.engine.money import ENGINE_CONTEXT, ONE, ZERO, dsum, quantize
from app.services.engine.outputs import (
    Calibration,
    ConfidenceOut,
    CostLineOut,
    EstimateResult,
    GroupTotal,
    ManpowerRow,
    RangeDriver,
    SanityCheck,
    SpreadFactor,
    Timeline,
    Totals,
)
from app.services.engine.reference import PLACEHOLDER
from app.services.engine.run_costs import ai_runtime_lines, maintenance_lines
from app.services.engine.simulation import simulate
from app.services.engine.third_party import (
    client_paid_lines,
    client_paid_notes,
    dev_tools_lines,
    third_party_lines,
    translation_lines,
)
from app.services.engine.timeline import build_timeline, phased_plan, size_band
from app.services.hosting.sizing import hosting_lines

ENGINE_VERSION = "1.0.0"
TOP_DRIVERS = 3
QUANTUM = Decimal("0.01")
SCORE_QUANTUM = Decimal("0.001")
MAINTENANCE_BUCKETS = (
    "run.helpdesk",
    "run.patching_bugfix",
    "run.change_requests",
    "run.onsite_resources",
    "run.annual_audit",
    "run.ssl_domain",
)


def calculate(inp: EstimateInput) -> EstimateResult:
    with localcontext(ENGINE_CONTEXT):
        return _calculate(inp)


def _calculate(inp: EstimateInput) -> EstimateResult:
    ctx = PricingContext(inp)
    p = inp.parameters
    for group in ("calendar", "timeline"):
        if getattr(p, group).source == PLACEHOLDER:
            ctx.placeholders.add(f"param:{group}")
    runs = inp.monte_carlo_runs or p.uncertainty.monte_carlo_runs

    bucket_order = {b.key: b.order for b in inp.taxonomy.buckets}
    components = sorted(
        inp.components,
        key=lambda c: bucket_order[inp.catalog.get(c.catalog_key).bucket],
    )
    efforts = [base_effort(ctx, ci) for ci in components]
    timeline = build_timeline(ctx, efforts)
    common = {
        "engine_version": ENGINE_VERSION,
        "seed": inp.seed,
        "monte_carlo_runs": runs,
        "versions": {
            "rate_card": inp.rate_card.version,
            "parameters": p.version,
            "catalog": inp.catalog.version,
            "taxonomy": inp.taxonomy.version,
        },
        "timeline": timeline,
        "confidence": _confidence(ctx),
        "assumptions": ctx.assumptions(),
    }

    if timeline.status == "not_feasible":
        return EstimateResult(
            feasible=False,
            infeasibility=phased_plan(ctx, efforts, timeline),
            lines=[],
            totals=None,
            by_stage=[],
            by_bucket=[],
            by_year=[],
            manpower=[],
            top_drivers=[],
            top_drivers_text="",
            calibration=_calibration(ctx),
            sanity_checks=[],
            **common,  # type: ignore[arg-type]
        )

    m = timeline.compression_multiplier
    _, band = size_band(ctx, timeline.build_effort_pd)
    base: list[CostLineOut] = [component_line(ctx, e, m) for e in efforts]
    base += ai_review_line(ctx, efforts, m)
    base += dev_tools_lines(ctx, base)
    base += translation_lines(ctx)
    base += golive_lines(ctx, timeline)
    base += hosting_lines(ctx)
    base += ai_runtime_lines(ctx)
    base += third_party_lines(ctx)
    base += maintenance_lines(ctx, timeline.build_effort_pd, band.audit_band)
    base += programme_lines(ctx, timeline)
    base += base_commercial_lines(ctx, timeline)
    derived, factors = derived_lines(ctx, timeline, base)

    lines = sorted(
        base + derived,
        key=lambda ln: (bucket_order[ln.bucket], ln.year, ln.line_key),
    )
    keys = [ln.line_key for ln in lines]
    if len(keys) != len(set(keys)):
        raise AssertionError("duplicate line keys")

    spread = _model_spread(ctx)
    sim = simulate(
        lines, factors, inp.seed, runs, inp.taxonomy, (spread.down, spread.up) if spread else None
    )
    client_paid = client_paid_lines(ctx)
    notes = client_paid_notes(ctx)
    totals = Totals(
        likely_paise=sum(ln.likely_paise for ln in lines),
        low_sum_paise=sum(ln.low_paise for ln in lines),
        high_sum_paise=sum(ln.high_paise for ln in lines),
        p10_paise=sim.p10_paise,
        p50_paise=sim.p50_paise,
        p90_paise=sim.p90_paise,
    )
    stage_names = {s.key: s.name for s in inp.taxonomy.stages}
    stage_order = {s.key: s.order for s in inp.taxonomy.stages}
    bucket_names = {b.key: b.name for b in inp.taxonomy.buckets}
    top = sim.drivers[:TOP_DRIVERS]
    return EstimateResult(
        feasible=True,
        infeasibility=None,
        lines=lines,
        totals=totals,
        by_stage=_group(lines, lambda ln: ln.stage, stage_names, stage_order),
        by_bucket=_group(lines, lambda ln: ln.bucket, bucket_names, bucket_order),
        by_year=_group(
            lines,
            lambda ln: str(ln.year),
            {str(y): ("Build / one-off" if y == 0 else f"O&M year {y}") for y in range(0, 100)},
            {str(y): y for y in range(0, 100)},
        ),
        manpower=_manpower(ctx, lines, timeline),
        top_drivers=top,
        top_drivers_text=_drivers_text(top),
        calibration=_calibration(ctx),
        sanity_checks=_sanity(ctx, lines),
        client_paid=client_paid,
        client_paid_notes=notes,
        **common,  # type: ignore[arg-type]
    )


def _group(
    lines: Iterable[CostLineOut],
    key: Callable[[CostLineOut], str],
    names: dict[str, str],
    order: dict[str, int],
) -> list[GroupTotal]:
    acc: dict[str, list[int]] = defaultdict(lambda: [0, 0, 0])
    for ln in lines:
        a = acc[key(ln)]
        a[0] += ln.likely_paise
        a[1] += ln.low_paise
        a[2] += ln.high_paise
    return [
        GroupTotal(key=k, name=names[k], likely_paise=v[0], low_paise=v[1], high_paise=v[2])
        for k, v in sorted(acc.items(), key=lambda kv: order[kv[0]])
    ]


def _manpower(
    ctx: PricingContext, lines: Iterable[CostLineOut], timeline: Timeline
) -> list[ManpowerRow]:
    """Roles × stage × year: person-days, person-months and average FTE over the period
    (delivery duration for build stages, programme duration for programme, a year for O&M)."""
    cal = ctx.p.calendar
    acc: dict[tuple[str, str, int], Decimal] = defaultdict(lambda: ZERO)
    for ln in lines:
        for role, pd in ln.role_pd.items():
            acc[(role, ln.stage, ln.year)] += pd
    rows = []
    for (role, stage, year), pd in sorted(
        acc.items(), key=lambda kv: (kv[0][2], kv[0][1], kv[0][0])
    ):
        pm = pd / cal.pd_per_month
        if year > 0:
            months = cal.pd_per_year / cal.pd_per_month
        elif stage == "programme":
            months = timeline.programme_duration_months
        else:
            months = timeline.delivery_duration_months
        rows.append(
            ManpowerRow(
                role=role,
                stage=stage,
                year=year,
                person_days=quantize(pd, QUANTUM),
                person_months=quantize(pm, QUANTUM),
                average_fte=quantize(pm / months, QUANTUM),
            )
        )
    return rows


def _drivers_text(drivers: list[RangeDriver]) -> str:
    if not drivers:
        return ""
    parts = [f"{d.name} ({d.variance_share * 100:.0f}%)" for d in drivers]
    joined = parts[0] if len(parts) == 1 else ", ".join(parts[:-1]) + f" and {parts[-1]}"
    verb = "contributes" if len(parts) == 1 else "contribute"
    return f"{joined} {verb} most of the range."


def _confidence(ctx: PricingContext) -> ConfidenceOut:
    c = ctx.p.confidence
    if c.source == PLACEHOLDER:
        ctx.placeholders.add("param:confidence")
    clarity_score = (ctx.overall_clarity() - ONE) / Decimal(4)  # clarity 1..5 -> 0..1
    template = c.template_score[ctx.inp.template_match]
    age = (ctx.inp.as_of_date - ctx.inp.rate_card.effective_date).days
    if age <= c.fresh_days:
        fresh = ONE
    elif age >= c.stale_days:
        fresh = ZERO
    else:
        fresh = Decimal(c.stale_days - age) / Decimal(c.stale_days - c.fresh_days)
    score = (
        c.weight_clarity * clarity_score + c.weight_template * template + c.weight_freshness * fresh
    )
    label: Literal["high", "medium", "low"] = (
        "high" if score >= c.high_threshold else "medium" if score >= c.medium_threshold else "low"
    )
    return ConfidenceOut(
        label=label,
        score=quantize(score, SCORE_QUANTUM),
        clarity_component=quantize(clarity_score, SCORE_QUANTUM),
        template_component=quantize(template, SCORE_QUANTUM),
        freshness_component=quantize(fresh, SCORE_QUANTUM),
        rate_card_age_days=age,
    )


def _model_spread(ctx: PricingContext) -> SpreadFactor | None:
    """The back-tested model error for this project size (parameter sets v12+) or else this
    buyer segment, if the parameter set has one."""
    cal = ctx.p.calibration
    if cal is None:
        return None
    size = ctx.q.project_size
    if size is not None and size in cal.model_spread_by_size:
        s = cal.model_spread_by_size[size]
        return SpreadFactor(
            name=f"model error ({size} projects, back-tested)", down=s.down, up=s.up
        )
    segment = ctx.q.buyer_segment
    if segment not in cal.model_spread:
        return None
    s = cal.model_spread[segment]
    return SpreadFactor(name=f"model error ({segment}, back-tested)", down=s.down, up=s.up)


def _calibration(ctx: PricingContext) -> Calibration:
    refs = sorted(ctx.placeholders)
    return Calibration(
        status="uncalibrated" if refs else "calibrated",
        placeholder_refs=refs,
        model_spread=_model_spread(ctx),
    )


def _sanity(ctx: PricingContext, lines: list[CostLineOut]) -> list[SanityCheck]:
    """Bottom-up annual maintenance vs the 15–25 %-of-build rule of thumb (year 1)."""
    mt = ctx.p.maintenance
    build = dsum(Decimal(ln.likely_paise) for ln in lines if ln.stage in ("pre_build", "build"))
    year1 = dsum(
        Decimal(ln.likely_paise)
        for ln in lines
        if ln.year == 1 and ln.bucket in MAINTENANCE_BUCKETS
    )
    if build == ZERO or ctx.q.om_years == 0:
        return []
    ratio = year1 / build
    pct = f"{ratio * 100:.1f}%"
    band = f"{mt.rule_of_thumb_low * 100:.0f}–{mt.rule_of_thumb_high * 100:.0f}%"
    ok = mt.rule_of_thumb_low <= ratio <= mt.rule_of_thumb_high
    return [
        SanityCheck(
            key="maintenance_rule_of_thumb",
            status="ok" if ok else "flag",
            message=(
                f"Year-1 maintenance is {pct} of build cost; the industry rule of thumb is "
                f"{band}." + ("" if ok else " Review the maintenance drivers.")
            ),
        )
    ]

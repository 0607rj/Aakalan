"""Timeline: natural duration, deadline compression / extension and feasibility (brief 7.3)."""

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal

from app.services.engine.components import ComponentEffort
from app.services.engine.context import LineBuilder, PricingContext
from app.services.engine.money import ONE, ZERO, ceil_to, dsum, interpolate
from app.services.engine.outputs import Infeasibility, PhaseSuggestion, Timeline
from app.services.engine.reference import SizeBand


@dataclass(frozen=True)
class Natural:
    effort_pd: Decimal
    effort_pm: Decimal
    max_team: Decimal
    months: Decimal


def natural_duration(ctx: PricingContext, effort_pd: Decimal) -> Natural:
    """natural_months = max(min_months, effort_pm / max_team(effort_pm)), rounded up to the
    duration quantum. max_team is piecewise linear with a positive intercept on every segment,
    so natural duration never decreases as effort grows."""
    tl = ctx.p.timeline
    effort_pm = effort_pd / ctx.p.calendar.pd_per_month
    team = interpolate(tl.max_team_curve, effort_pm)
    months = max(tl.min_duration_months, effort_pm / team)
    return Natural(effort_pd, effort_pm, team, ceil_to(months, tl.duration_quantum_months))


def size_band(ctx: PricingContext, effort_pd: Decimal) -> tuple[int, SizeBand]:
    for i, band in enumerate(ctx.p.timeline.size_bands):
        if band.max_build_pd is None or effort_pd <= band.max_build_pd:
            return i, band
    raise ValueError("timeline.size_bands must end with an open-ended band")


@dataclass(frozen=True)
class BandMix:
    lower: int  # index of the band whose value applies at weight 0
    upper: int  # the next band (the same index outside a blend)
    weight: Decimal  # the upper band's share


def band_mix(ctx: PricingContext, effort_pd: Decimal) -> BandMix:
    """Where the build sits between the size bands. With timeline.size_band_blend_share = s
    (v23+), across band edge E: weight = (pd − E(1 − s)) / (2 E s) for E(1 − s) < pd < E(1 + s);
    elsewhere, and before v23, the band holding the build at weight 0."""
    idx, _ = size_band(ctx, effort_pd)
    s = ctx.p.timeline.size_band_blend_share
    bands = ctx.p.timeline.size_bands
    if s is not None:
        for i, band in enumerate(bands[:-1]):
            edge = band.max_build_pd
            if edge is None:
                break
            low, high = edge * (ONE - s), edge * (ONE + s)
            if low < effort_pd < high:
                return BandMix(i, i + 1, (effort_pd - low) / (high - low))
    return BandMix(idx, idx, ZERO)


def _blend(t: LineBuilder, mix: BandMix, label: str, low: Decimal, high: Decimal) -> Decimal:
    """low + (high − low) × weight, recorded as a step with the blend share it came from."""
    t.param("timeline", "size_band_blend_share")
    return t.step(
        f"{label} between the size bands",
        f"{low} + ({high} − {low}) × {mix.weight:.4f}",
        low + (high - low) * mix.weight,
    )


def band_value(t: LineBuilder, effort_pd: Decimal, field: str) -> Decimal:
    """size_bands[band][field] for this build size, blended across a band edge (band_mix)."""
    mix = band_mix(t.ctx, effort_pd)
    low: Decimal = t.param("timeline", "size_bands", mix.lower, field)
    if mix.upper == mix.lower:
        return low
    high: Decimal = t.param("timeline", "size_bands", mix.upper, field)
    return _blend(t, mix, field, low, high)


def band_fee(t: LineBuilder, effort_pd: Decimal, prefix: str) -> Decimal:
    """rate(prefix.audit_band) for this build size, blended across a band edge (band_mix)."""
    mix = band_mix(t.ctx, effort_pd)
    band: str = t.param("timeline", "size_bands", mix.lower, "audit_band")
    low = t.rate_local(f"{prefix}.{band}")
    if mix.upper == mix.lower:
        return low
    upper: str = t.param("timeline", "size_bands", mix.upper, "audit_band")
    return _blend(t, mix, f"{prefix} fee", low, t.rate_local(f"{prefix}.{upper}"))


def fastest_months(ctx: PricingContext, natural_months: Decimal) -> Decimal:
    """fastest = ceil_to(natural_months × infeasible_below_ratio, duration_quantum): the
    shortest deadline that still gets a price (a bigger team, priced by the compression curve)."""
    tl = ctx.p.timeline
    return ceil_to(natural_months * tl.infeasible_below_ratio, tl.duration_quantum_months)


def compression_multiplier(ctx: PricingContext, ratio: Decimal) -> Decimal:
    """1.0 at ratio >= 1; linear along compression_curve below it (extrapolated past its end)."""
    if ratio >= ONE:
        return ONE
    return interpolate(ctx.p.timeline.compression_curve, ratio, extrapolate=True)


def build_timeline(ctx: PricingContext, efforts: Sequence[ComponentEffort]) -> Timeline:
    effort_pd = dsum(e.effort_pd for e in efforts)
    nat = natural_duration(ctx, effort_pd)
    _, band = size_band(ctx, effort_pd)
    deadline = ctx.q.deadline_months
    infeasible_below = ctx.p.timeline.infeasible_below_ratio
    ratio: Decimal | None = None
    multiplier = ONE
    delivery = programme = nat.months
    status = "natural"
    if deadline is not None:
        ratio = deadline / nat.months
        if ratio < infeasible_below:
            status = "not_feasible"
        elif ratio < ONE:
            status = "compressed"
            multiplier = compression_multiplier(ctx, ratio)
            delivery = deadline
            if ctx.p.timeline.programme_follows_deadline:
                # v17+: the squeeze is paid once, in the build effort; the programme then
                # runs over the same shorter period.
                programme = deadline
        elif ratio > ONE and not ctx.p.timeline.longer_deadline_builds_at_natural:
            status = "extended"
            delivery = programme = deadline
    return Timeline(
        build_effort_pd=effort_pd,
        build_effort_person_months=nat.effort_pm,
        max_team=nat.max_team,
        natural_duration_months=nat.months,
        deadline_months=deadline,
        delivery_duration_months=delivery,
        programme_duration_months=programme,
        compression_ratio=ratio,
        compression_multiplier=multiplier,
        size_band=band.name,
        status=status,  # type: ignore[arg-type]
    )


def phased_plan(
    ctx: PricingContext, efforts: Sequence[ComponentEffort], timeline: Timeline
) -> Infeasibility:
    """Greedy phase split when the deadline is below the feasibility floor: phase 1 takes
    components in order while natural_duration(phase effort) × floor ratio fits the deadline."""
    assert timeline.deadline_months is not None
    floor = ctx.p.timeline.infeasible_below_ratio
    phases: list[list[ComponentEffort]] = [[]]
    for e in efforts:
        candidate = [*phases[-1], e]
        months = natural_duration(ctx, dsum(c.effort_pd for c in candidate)).months
        if phases[-1] and months * floor > timeline.deadline_months:
            phases.append([e])
        else:
            phases[-1] = candidate
    suggestions = []
    for i, group in enumerate(phases, start=1):
        pd = dsum(c.effort_pd for c in group)
        suggestions.append(
            PhaseSuggestion(
                phase=i,
                component_instance_ids=[c.instance.id for c in group],
                build_effort_pd=pd,
                natural_duration_months=natural_duration(ctx, pd).months,
            )
        )
    minimum = fastest_months(ctx, timeline.natural_duration_months)
    return Infeasibility(
        message=(
            f"A {timeline.deadline_months}-month deadline is below "
            f"{floor * 100:.0f}% of the natural duration "
            f"({timeline.natural_duration_months} months). No price is given; deliver in "
            f"{len(suggestions)} phases or extend the deadline to at least {minimum} months."
        ),
        minimum_feasible_months=minimum if minimum > ZERO else ONE,
        phases=suggestions,
    )

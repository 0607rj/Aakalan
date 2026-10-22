"""Timeline: natural duration, deadline compression / extension and feasibility (brief 7.3)."""

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal

from app.services.engine.components import ComponentEffort
from app.services.engine.context import PricingContext
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
        elif ratio > ONE:
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
    minimum = ceil_to(
        timeline.natural_duration_months * floor, ctx.p.timeline.duration_quantum_months
    )
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

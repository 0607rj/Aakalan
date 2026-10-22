"""Go-live (audit, certification, training, hypercare) and programme (PM, steering, MIS,
travel, environments) lines."""

from decimal import Decimal

from app.services.engine import spreads
from app.services.engine.context import LineBuilder, PricingContext
from app.services.engine.money import ONE, ZERO, ceil
from app.services.engine.outputs import CostLineOut, Timeline
from app.services.engine.timeline import size_band


def _band(t: LineBuilder, timeline: Timeline) -> int:
    idx, _ = size_band(t.ctx, timeline.build_effort_pd)
    t.param("timeline", "size_bands", idx)
    t.step("build effort", "Σ component effort (pd, before compression)", timeline.build_effort_pd)
    return idx


def golive_lines(ctx: PricingContext, timeline: Timeline) -> list[CostLineOut]:
    lines: list[CostLineOut] = []
    overall = ctx.overall_clarity()

    t = ctx.builder(
        line_key="go_live.security_audit/cert_in",
        stage="go_live",
        bucket="go_live.security_audit",
        year=0,
        label="CERT-In empanelled security audit",
        formula_id="golive.cert_in_audit.v1",
    )
    if t.driver("cert_in_audit"):
        idx = _band(t, timeline)
        audit_band: str = t.param("timeline", "size_bands", idx, "audit_band")
        prefix: str = t.param("go_live", "cert_in_audit_rate_prefix")
        fee = t.rate_local(f"{prefix}.{audit_band}")
        spreads.fixed(t, "fixed_fee")
        lines.append(t.finish(fee))

        r = t.fork(
            line_key="go_live.security_audit/cert_in_reaudit",
            label="CERT-In re-audit after remediation",
            formula_id="golive.cert_in_reaudit.v1",
        )
        re_prefix: str = r.param("go_live", "cert_in_reaudit_rate_prefix")
        spreads.fixed(r, "fixed_fee")
        lines.append(r.finish(r.rate_local(f"{re_prefix}.{audit_band}")))

    t = ctx.builder(
        line_key="go_live.certification/stqc",
        stage="go_live",
        bucket="go_live.certification",
        year=0,
        label="STQC certification",
        formula_id="golive.stqc.v1",
    )
    if t.driver("stqc_certification"):
        fee = t.rate_local(t.param("go_live", "stqc_rate_key"))
        spreads.fixed(t, "fixed_fee")
        lines.append(t.finish(fee))

    t = ctx.builder(
        line_key="go_live.training/labour",
        stage="go_live",
        bucket="go_live.training",
        year=0,
        label="Training delivery",
        formula_id="golive.training_labour.v1",
    )
    sessions: int = t.driver("training_sessions")
    if sessions:
        pd_per: Decimal = t.param("go_live", "training_pd_per_session")
        role: str = t.param("go_live", "trainer_role")
        pd = t.step("trainer person-days", f"{sessions} × {pd_per}", sessions * pd_per)
        t.add_role_pd(role, pd)
        spreads.clarity(t, overall)
        lines.append(t.finish(pd * t.rate_local(role)))

    t = ctx.builder(
        line_key="go_live.training/travel",
        stage="go_live",
        bucket="go_live.training",
        year=0,
        label="Training travel (outstation sessions)",
        formula_id="golive.training_travel.v1",
    )
    outstation: int = t.driver("training_outstation_sessions")
    if outstation:
        trips: Decimal = t.param("go_live", "trips_per_outstation_session")
        trip_rate = t.rate_local(t.param("go_live", "travel_rate_key"))
        spreads.clarity(t, overall)
        lines.append(t.finish(outstation * trips * trip_rate))

    t = ctx.builder(
        line_key="go_live.hypercare/team",
        stage="go_live",
        bucket="go_live.hypercare",
        year=0,
        label="Hypercare after go-live",
        formula_id="golive.hypercare.v1",
    )
    weeks: int = t.driver("hypercare_weeks")
    if weeks:
        pd_per_week: Decimal = t.param("go_live", "pd_per_week")
        team: dict[str, Decimal] = t.param("go_live", "hypercare_team_fte")
        scale = ONE
        if t.lean():
            t.formula_id = "golive.hypercare.v2"
            full = weeks * pd_per_week * sum(team.values(), ZERO)
            share: Decimal = t.param("lean", "hypercare_share_of_build_pd")
            t.step("build effort", "Σ component effort (pd)", timeline.build_effort_pd)
            cap = share * timeline.build_effort_pd
            scale = t.step(
                "lean hypercare scale",
                f"min(1, {share} × {timeline.build_effort_pd:.2f} / {full:.2f})",
                min(ONE, cap / full) if full else ONE,
            )
        total = ZERO
        for role, fte in team.items():
            pd = weeks * pd_per_week * fte * scale
            t.add_role_pd(role, pd)
            total += t.step(
                f"hypercare {role}",
                f"{weeks} wk × {pd_per_week} × {fte} FTE × {scale:.4f}",
                pd * t.rate_local(role),
            )
        spreads.clarity(t, overall)
        lines.append(t.finish(total))
    return lines


def programme_lines(ctx: PricingContext, timeline: Timeline) -> list[CostLineOut]:
    """Programme costs over max(deadline, natural duration) — compression does not shorten
    the management load; an extended deadline adds months of overhead. With
    timeline.programme_follows_deadline (v17+), a squeezed build runs its programme over the
    deadline instead, since the squeeze is already paid in the build effort."""
    lines: list[CostLineOut] = []
    overall = ctx.overall_clarity()
    months = timeline.programme_duration_months

    def base(key: str, bucket: str, label: str, formula: str) -> LineBuilder:
        t = ctx.builder(
            line_key=f"{bucket}/{key}",
            stage="programme",
            bucket=bucket,
            year=0,
            label=label,
            formula_id=formula,
            uncertainty_group="programme",
        )
        t.driver("deadline_months")
        squeezed = timeline.status == "compressed" and ctx.p.timeline.programme_follows_deadline
        t.step(
            "programme months",
            "deadline (the build is squeezed into it)"
            if squeezed
            else f"max(deadline, natural {timeline.natural_duration_months})",
            months,
        )
        t.add_input(programme_months=str(months))
        spreads.clarity(t, overall)
        return t

    t = base("pm", "programme.project_management", "Project management (build)", "programme.pm.v1")
    idx = _band(t, timeline)
    fte: Decimal = t.param("timeline", "size_bands", idx, "pm_fte")
    pd_month: Decimal = t.param("calendar", "pd_per_month")
    pm_role: str = t.param("programme", "pm_role")
    pd = t.step("PM person-days", f"{fte} FTE × {months} × {pd_month}", fte * months * pd_month)
    if t.lean():
        t.formula_id = "programme.pm.v2"
        share: Decimal = t.param("lean", "pm_share_of_build_pd")
        pd = t.step(
            "lean PM person-days",
            f"min({pd:.2f}, {share} × {timeline.build_effort_pd:.2f})",
            min(pd, share * timeline.build_effort_pd),
        )
    t.add_role_pd(pm_role, pd)
    lines.append(t.finish(pd * t.rate_local(pm_role)))

    if ctx.q.governance_overheads:
        t = base(
            "steering",
            "programme.steering_meetings",
            "Steering committee meetings",
            "programme.steering.v1",
        )
        interval: Decimal = t.param("programme", "steering_interval_months")
        meetings = t.step("meetings", f"ceil({months} / {interval})", ceil(months / interval))
        lines.append(t.finish(meetings * t.rate_local(t.param("programme", "steering_rate_key"))))

        t = base("mis", "programme.mis_reports", "MIS reports", "programme.mis.v1")
        mis_pd: Decimal = t.param("programme", "mis_pd_per_month")
        mis_role: str = t.param("programme", "mis_role")
        pd = t.step("MIS person-days", f"{months} × {mis_pd}", months * mis_pd)
        t.add_role_pd(mis_role, pd)
        lines.append(t.finish(pd * t.rate_local(mis_role)))

        t = base("travel", "programme.travel", "Programme travel", "programme.travel.v1")
        trips: Decimal = t.param("programme", "travel_trips_per_month")
        lines.append(
            t.finish(months * trips * t.rate_local(t.param("programme", "travel_rate_key")))
        )

    t = base(
        "envs", "programme.environments", "Non-production environments", "programme.environments.v1"
    )
    envs: Decimal = t.param("programme", "non_prod_environments")
    if ctx.q.non_prod_environments is not None:
        t.driver("non_prod_environments")
        envs = Decimal(ctx.q.non_prod_environments)
    lean_key = ctx.p.lean.environment_rate_key if ctx.p.lean else None
    by_provider = ctx.p.programme.environment_rate_key_by_provider
    if ctx.q.hosting_provider in by_provider:
        # v17+: test servers on the same provider as production
        t.driver("hosting_provider")
        env_rate = t.rate_local(
            t.param("programme", "environment_rate_key_by_provider", ctx.q.hosting_provider)
        )
    elif lean_key and t.lean():
        env_rate = t.rate_local(t.param("lean", "environment_rate_key"))
    else:
        env_rate = t.rate_local(t.param("programme", "environment_rate_key"))
    lines.append(t.finish(months * envs * env_rate))

    for year in range(1, ctx.q.om_years + 1):
        t = ctx.builder(
            line_key=f"programme.project_management/om_y{year}",
            stage="programme",
            bucket="programme.project_management",
            year=year,
            label=f"Project management (O&M year {year})",
            formula_id="programme.om_pm.v1",
            uncertainty_group="programme",
        )
        t.driver("om_years")
        fte = t.param("timeline", "size_bands", idx, "om_pm_fte")
        pd_year: Decimal = t.param("calendar", "pd_per_year")
        pd = fte * pd_year
        if t.lean():
            t.formula_id = "programme.om_pm.v2"
            om_share: Decimal = t.param("lean", "om_pm_share_of_build_pd")
            pd = t.step(
                "lean O&M PM person-days",
                f"min({pd:.2f}, {om_share} × {timeline.build_effort_pd:.2f})",
                min(pd, om_share * timeline.build_effort_pd),
            )
        t.add_role_pd(pm_role, pd)
        esc = t.escalation("labour", year)
        spreads.clarity(t, overall)
        spreads.om_year(t, year)
        lines.append(t.finish(pd * t.rate_local(pm_role) * esc))
    return lines

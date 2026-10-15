"""Run costs per O&M year (brief 7.4): AI runtime, maintenance, licences. Hosting lines come
from `services/hosting`."""

from decimal import Decimal

from app.services.engine import spreads
from app.services.engine.context import LineBuilder, PricingContext
from app.services.engine.money import ONE, ceil
from app.services.engine.outputs import CostLineOut


def _run(
    ctx: PricingContext, key: str, bucket: str, year: int, label: str, formula: str
) -> LineBuilder:
    t = ctx.builder(
        line_key=f"{bucket}/{key}/y{year}",
        stage="run",
        bucket=bucket,
        year=year,
        label=f"{label} (year {year})",
        formula_id=formula,
    )
    t.driver("om_years")
    return t


def ai_runtime_lines(ctx: PricingContext) -> list[CostLineOut]:
    lines: list[CostLineOut] = []
    if ctx.q.chatbot_queries_per_day == 0:
        return lines
    for year in range(1, ctx.q.om_years + 1):
        if ctx.q.ai_runtime_mode == "api":
            t = _run(ctx, "llm_api", "run.ai_runtime", year, "LLM API tokens", "ai_runtime.api.v1")
            q: int = t.driver("chatbot_queries_per_day")
            tin: int = t.driver("tokens_in_per_query")
            tout: int = t.driver("tokens_out_per_query")
            t.driver("ai_runtime_mode")
            days: Decimal = t.param("calendar", "days_per_year")
            growth: Decimal = t.param("ai_runtime", "volume_growth_per_year")
            per_unit: Decimal = t.param("ai_runtime", "tokens_per_unit")
            change: Decimal = t.param("ai_runtime", "annual_price_change")
            p_in = t.rate_inr(t.param("ai_runtime", "token_input_rate_key"))
            p_out = t.rate_inr(t.param("ai_runtime", "token_output_rate_key"))
            queries = t.step(
                "queries per year",
                f"{q} × {days} × (1 + {growth})^{year - 1}",
                q * days * (ONE + growth) ** (year - 1),
            )
            per_query = t.step(
                "₹ per query",
                f"({tin} × {p_in:.4f} + {tout} × {p_out:.4f}) / {per_unit}",
                (tin * p_in + tout * p_out) / per_unit,
            )
            cost = queries * per_query * (ONE + change) ** year
        else:
            t = _run(
                ctx, "gpu", "run.ai_runtime", year, "Self-hosted GPU inference", "ai_runtime.gpu.v1"
            )
            t.driver("ai_runtime_mode")
            q = t.driver("chatbot_queries_per_day")
            pattern: str = t.param("hosting", "pattern_by_sla", t.driver("uptime_sla"))
            growth = t.param("ai_runtime", "volume_growth_per_year")
            peak: Decimal = t.param("ai_runtime", "peak_factor")
            per_gpu: Decimal = t.param("ai_runtime", "queries_per_second_per_gpu")
            min_gpus: Decimal = t.param("ai_runtime", "min_gpus", pattern)
            secs: Decimal = t.param("calendar", "seconds_per_day")
            qps = t.step(
                "peak queries / second",
                f"{q} × (1 + {growth})^{year - 1} / {secs} × {peak}",
                q * (ONE + growth) ** (year - 1) / secs * peak,
            )
            gpus = t.step(
                "GPUs",
                f"max({min_gpus}, ceil(qps / {per_gpu}))",
                max(min_gpus, ceil(qps / per_gpu)),
            )
            hours: Decimal = t.param("calendar", "hours_per_year")
            rate = t.rate_inr(t.param("ai_runtime", "gpu_rate_key"))
            cost = gpus * hours * rate * t.escalation("prices", year)
        spreads.fixed(t, "ai_runtime")
        spreads.om_year(t, year)
        lines.append(t.finish(cost))
    return lines


def maintenance_lines(
    ctx: PricingContext, build_effort_pd: Decimal, audit_band: str
) -> list[CostLineOut]:
    """Bottom-up maintenance: helpdesk, bug-fix, patching, upgrades, change requests, onsite
    staff, annual re-audit, SSL/domain and licences, escalated per year."""
    lines: list[CostLineOut] = []
    clarity = ctx.overall_clarity()
    pd_year = ctx.p.calendar.pd_per_year

    def labour(t: LineBuilder, pd: Decimal, role: str, year: int) -> CostLineOut:
        t.add_role_pd(role, pd)
        esc = t.escalation("labour", year)
        spreads.clarity(t, clarity)
        spreads.om_year(t, year)
        return t.finish(pd * t.rate_inr(role) * esc)

    def price(t: LineBuilder, amount: Decimal, year: int) -> CostLineOut:
        esc = t.escalation("prices", year)
        spreads.fixed(t, "fixed_fee")
        spreads.om_year(t, year)
        return t.finish(amount * esc)

    for year in range(1, ctx.q.om_years + 1):
        t = _run(ctx, "helpdesk", "run.helpdesk", year, "Helpdesk", "maintenance.helpdesk.v1")
        users: int = t.driver("users_total")
        tiers = ctx.p.maintenance.helpdesk_seats_by_users
        tier = next(i for i, x in enumerate(tiers) if x.max_users is None or users <= x.max_users)
        seats: Decimal = t.param("maintenance", "helpdesk_seats_by_users", tier, "seats")
        sla: str = t.driver("support_sla")
        coverage: Decimal = t.param("maintenance", "helpdesk_coverage_fte", sla)
        t.param("calendar", "pd_per_year")
        pd = t.step(
            "helpdesk person-days", f"{seats} × {coverage} × {pd_year}", seats * coverage * pd_year
        )
        lines.append(labour(t, pd, t.param("maintenance", "helpdesk_role"), year))

        for item, label in (
            ("bugfix", "Bug-fix support"),
            ("patching", "Security patching"),
            ("upgrade", "Platform upgrades"),
        ):
            formula = "maintenance.upgrades.v1" if item == "upgrade" else f"maintenance.{item}.v1"
            t = _run(ctx, item, "run.patching_bugfix", year, label, formula)
            share: Decimal = t.param("maintenance", f"{item}_share_of_build_pd")
            t.step("build effort", "Σ component effort (pd)", build_effort_pd)
            pd = t.step(
                f"{item} person-days", f"{build_effort_pd:.2f} × {share}", build_effort_pd * share
            )
            lines.append(labour(t, pd, t.param("maintenance", f"{item}_role"), year))

        t = _run(
            ctx,
            "pool",
            "run.change_requests",
            year,
            "Change-request pool",
            "maintenance.change_requests.v1",
        )
        cr: Decimal | None = t.driver("change_request_pd_per_year")
        if cr is None:
            share = t.param("maintenance", "change_request_share_of_build_pd")
            cr = t.step(
                "CR person-days", f"{build_effort_pd:.2f} × {share}", build_effort_pd * share
            )
        if cr:
            lines.append(labour(t, cr, t.param("maintenance", "change_request_role"), year))

        for i, res in enumerate(ctx.q.onsite_resources):
            t = _run(
                ctx,
                f"onsite{i}",
                "run.onsite_resources",
                year,
                f"Onsite {res.role.removeprefix('role.')}",
                "maintenance.onsite.v1",
            )
            t.driver("onsite_resources")
            t.param("calendar", "pd_per_year")
            pd = t.step("onsite person-days", f"{res.count} × {pd_year}", res.count * pd_year)
            lines.append(labour(t, pd, res.role, year))

        t = _run(
            ctx,
            "audit",
            "run.annual_audit",
            year,
            "Annual security re-audit",
            "maintenance.annual_audit.v1",
        )
        if t.driver("cert_in_audit"):
            prefix: str = t.param("maintenance", "annual_audit_rate_prefix")
            lines.append(price(t, t.rate_inr(f"{prefix}.{audit_band}"), year))

        t = _run(
            ctx,
            "ssl_domain",
            "run.ssl_domain",
            year,
            "SSL certificate and domain",
            "maintenance.ssl_domain.v1",
        )
        amount = t.rate_inr(t.param("maintenance", "ssl_rate_key")) + t.rate_inr(
            t.param("maintenance", "domain_rate_key")
        )
        lines.append(price(t, amount, year))

        if ctx.q.licensing == "licensed":
            licence_keys = sorted(
                {
                    ctx.inp.catalog.get(c.catalog_key).licence.rate_key  # type: ignore[union-attr]
                    for c in ctx.inp.components
                    if ctx.inp.catalog.get(c.catalog_key).licence is not None
                }
            )
            for key in licence_keys:
                t = _run(
                    ctx, key, "run.licences", year, f"Licence {key.split('.')[1]}", "run.licence.v1"
                )
                t.driver("licensing")
                for c in ctx.inp.components:
                    lic = ctx.inp.catalog.get(c.catalog_key).licence
                    if lic is not None and lic.rate_key == key:
                        t.requirement_ids.extend(
                            r for r in c.requirement_ids if r not in t.requirement_ids
                        )
                lines.append(price(t, t.rate_inr(key), year))
    return lines

"""Run costs per O&M year (brief 7.4): AI runtime, maintenance, licences. Hosting lines come
from `services/hosting`."""

from decimal import Decimal

from app.services.engine import spreads
from app.services.engine.context import LineBuilder, PricingContext
from app.services.engine.inputs import OnsiteResource
from app.services.engine.money import ONE, ZERO, ceil, interpolate
from app.services.engine.outputs import CostLineOut
from app.services.engine.reference import Point
from app.services.engine.timeline import band_fee

OFFICE_HOURS = "8x5"  # the support hours dedicated support staff cover (support_staff.v1)
ROUND_THE_CLOCK = "24x7"  # people per round-the-clock seat: helpdesk_coverage_fte[this]
MONTHS_A_YEAR = 12  # calendar months, for staff needed for part of the support period
WEEKS_A_YEAR = 52  # calendar weeks, for the hypercare weeks inside support year 1


def _v2(res: OnsiteResource) -> bool:
    """Staff for part of the support period, or round-the-clock seats (OPEN_QUESTIONS 162)."""
    return res.months is not None or res.seats


def year_pd(ctx: PricingContext, res: OnsiteResource, year: int) -> Decimal:
    """A staff line's person-days in a support year, as its own line prices them (staff_pd):
    count (× people per round-the-clock seat) × pd_per_year × share of the year, or count × days
    in the first support year when the document limits their days."""
    if res.days is not None:
        return res.count * res.days if year == 1 else ZERO
    people = res.count
    if res.seats:
        people *= ctx.p.maintenance.helpdesk_coverage_fte[ROUND_THE_CLOCK]
    pd = people * ctx.p.calendar.pd_per_year
    if res.months is None:
        return pd
    year_months = Decimal(MONTHS_A_YEAR)
    return pd * min(max(res.months - year_months * (year - 1), ZERO), year_months) / year_months


def staff_doing(ctx: PricingContext, covers: str, year: int) -> tuple[Decimal, list[str]]:
    """Person-days this support year of the onsite staff whose line says they do `covers`
    work (parameter sets v25+, maintenance.staff_replace_work), and their names."""
    if not ctx.p.maintenance.staff_replace_work:
        return ZERO, []
    found = [r for r in ctx.q.onsite_resources if r.kind == "onsite" and r.covers == covers]
    return sum((year_pd(ctx, r, year) for r in found), ZERO), [r.name or r.role for r in found]


def after_hypercare(t: LineBuilder, year: int) -> Decimal:
    """Share of support year 1 after the hypercare weeks (parameter sets v25+,
    maintenance.hypercare_in_year_one): (weeks_a_year − hypercare_weeks) / weeks_a_year; 1 in
    other years or before v25. Hypercare is priced at go-live, so those weeks are not again."""
    if year != 1 or not t.ctx.p.maintenance.hypercare_in_year_one:
        return ONE
    weeks: Decimal = t.driver("hypercare_weeks")
    if not weeks:
        return ONE
    t.param("maintenance", "hypercare_in_year_one")
    year_weeks = Decimal(WEEKS_A_YEAR)
    return t.step(
        "share of year 1 after hypercare",
        f"({year_weeks} − {weeks}) / {year_weeks}",
        max(year_weeks - weeks, ZERO) / year_weeks,
    )


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
            p_in, p_out = t.token_rates()
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
            rate = t.rate_local(t.param("ai_runtime", "gpu_rate_key"))
            cost = gpus * hours * rate * t.escalation("prices", year)
        spreads.fixed(t, "ai_runtime")
        spreads.om_year(t, year)
        lines.append(t.finish(cost))
    return lines


def _ssl_and_domain(t: LineBuilder) -> Decimal:
    """One year's SSL certificate and web address (maintenance.ssl_domain.v1 / v2):

    v1: ssl_rate + domain_rate
    v2: ssl_rate[ssl_type] (0 when the client provides it) + domain_rate[web_domain] (0 when
        the client provides it); the answers cite the clause that says so.
    """
    ctx, mt = t.ctx, t.ctx.p.maintenance
    v2 = bool(mt.ssl_rate_key_by_type) or not ctx.q.ssl_in_scope or not ctx.q.domain_in_scope
    if v2:
        t.formula_id = "maintenance.ssl_domain.v2"
    ssl = ZERO
    if v2 and not t.driver("ssl_in_scope"):
        t.step("SSL certificate", "provided by the client", ZERO)
    else:
        ssl_key: str = (
            t.param("maintenance", "ssl_rate_key_by_type", t.driver("ssl_type"))
            if mt.ssl_rate_key_by_type
            else t.param("maintenance", "ssl_rate_key")
        )
        ssl = t.rate_local(ssl_key)
    domain = ZERO
    if v2 and not t.driver("domain_in_scope"):
        t.step("web address", "provided by the client", ZERO)
    else:
        domain_key: str = (
            t.param("maintenance", "domain_rate_key_by_type", t.driver("web_domain"))
            if mt.domain_rate_key_by_type
            else t.param("maintenance", "domain_rate_key")
        )
        domain = t.rate_local(domain_key)
    return ssl + domain


def maintenance_lines(ctx: PricingContext, build_effort_pd: Decimal) -> list[CostLineOut]:
    """Bottom-up maintenance: helpdesk, bug-fix, patching, upgrades, change requests, onsite
    staff, annual re-audit, SSL/domain and licences, escalated per year."""
    lines: list[CostLineOut] = []
    clarity = ctx.overall_clarity()
    pd_year = ctx.p.calendar.pd_per_year

    def labour(
        t: LineBuilder, pd: Decimal, role: str, year: int, *, scaled: bool = True
    ) -> CostLineOut:
        if scaled:  # mandated onsite staff are not scaled by calibration
            run = t.calibration("run_multiplier")
            pd = t.step("support effort × run multiplier", f"{pd:.2f} × {run}", pd * run)
        t.add_role_pd(role, pd)
        esc = t.escalation("labour", year)
        spreads.clarity(t, clarity)
        spreads.om_year(t, year)
        return t.finish(pd * t.rate_local(role) * esc)

    def price(t: LineBuilder, amount: Decimal, year: int) -> CostLineOut:
        esc = t.escalation("prices", year)
        spreads.fixed(t, "fixed_fee")
        spreads.om_year(t, year)
        return t.finish(amount * esc)

    def staff_pd(t: LineBuilder, res: OnsiteResource, year: int, what: str) -> Decimal:
        """count × pd_per_year (v1); with months or seats (v2, OPEN_QUESTIONS 162):
        count × people_per_seat (seats only) × pd_per_year × share_of_year, where
        share_of_year = clamp(months − 12 × (year − 1), 0, 12) / 12."""
        t.param("calendar", "pd_per_year")
        people = res.count
        if res.seats:
            per_seat: Decimal = t.param("maintenance", "helpdesk_coverage_fte", ROUND_THE_CLOCK)
            people = t.step(
                "people for the round-the-clock seats (assumption: people per seat)",
                f"{res.count} × {per_seat}",
                res.count * per_seat,
            )
        full = f"{what} person-days" if res.months is None else f"{what} person-days a full year"
        pd = t.step(full, f"{people} × {pd_year}", people * pd_year)
        if res.months is None:
            return pd
        year_months = Decimal(MONTHS_A_YEAR)
        months = min(max(res.months - year_months * (year - 1), ZERO), year_months)
        share = t.step(
            "share of this year they are needed",
            f"clamp({res.months} − {year_months} × {year - 1}, 0, {year_months}) / {year_months}",
            months / year_months,
        )
        return t.step(f"{what} person-days", f"{pd:.2f} × {share:.4f}", pd * share)

    def staff_label(res: OnsiteResource, default: str) -> str:
        return f"{default}: {res.name}" if res.name else default

    def support_staff_line(
        res: OnsiteResource, i: int, year: int, covered: Decimal
    ) -> tuple[CostLineOut | None, Decimal]:
        """maintenance.support_staff.v1/v2: a stated number of dedicated support staff is the
        least support labour, not more of it (OPEN_QUESTIONS 157). They do the support work
        already priced this year (the helpdesk in office hours, bug-fix, patching, upgrades,
        change requests), so only the shortfall is added:
        max(staff person-days (staff_pd) − that work's person-days, 0)."""
        t = _run(
            ctx,
            f"onsite{i}",
            "run.onsite_resources",
            year,
            staff_label(res, "Dedicated support staff (beyond the support work above)"),
            "maintenance.support_staff.v2" if _v2(res) else "maintenance.support_staff.v1",
        )
        t.driver("onsite_resources")
        stated = staff_pd(t, res, year, "stated support staff")
        t.step("support work priced above this year (person-days)", f"{covered:.2f}", covered)
        pd = t.step(
            "shortfall to the stated staff",
            f"max({stated:.2f} − {covered:.2f}, 0)",
            max(stated - covered, ZERO),
        )
        return (labour(t, pd, res.role, year, scaled=False) if pd else None), stated

    def upkeep_line(year: int) -> CostLineOut | None:
        """maintenance.upkeep.v1 (parameter sets v25+), one line a year:
        upkeep_pd = Σ build_effort_pd × share[bugfix, patching, upgrade] + change-request pd
        (stated, else build_effort_pd × change_request share), each at its own role;
        beyond = max(upkeep_pd − pd of the onsite staff who do this work, 0), shared pro rata;
        amount = Σ role pd × beyond / upkeep_pd × run multiplier × role rate
                 × (1 + escalation_labour)^year."""
        t = _run(
            ctx,
            "upkeep",
            "run.patching_bugfix",
            year,
            "Upkeep: bug fixes, security patches, upgrades and small changes",
            "maintenance.upkeep.v1",
        )
        t.follows_build = True
        t.step("build effort", "Σ component effort (pd)", build_effort_pd)
        parts: list[tuple[str, Decimal]] = []
        for item in ("bugfix", "patching", "upgrade"):
            share: Decimal = t.param("maintenance", f"{item}_share_of_build_pd")
            role: str = t.param("maintenance", f"{item}_role")
            pd = t.step(
                f"{item} person-days", f"{build_effort_pd:.2f} × {share}", build_effort_pd * share
            )
            parts.append((role, pd))
        cr: Decimal | None = t.driver("change_request_pd_per_year")
        if cr is None:
            share = t.param("maintenance", "change_request_share_of_build_pd")
            cr = t.step(
                "change-request person-days",
                f"{build_effort_pd:.2f} × {share}",
                build_effort_pd * share,
            )
        parts.append((t.param("maintenance", "change_request_role"), cr))
        total = t.step(
            "upkeep person-days",
            " + ".join(f"{pd:.2f}" for _, pd in parts),
            sum((pd for _, pd in parts), ZERO),
        )
        done, names = staff_doing(ctx, "upkeep", year)
        if done:
            t.driver("onsite_resources")
            t.param("maintenance", "staff_replace_work")
            t.step(f"done by the onsite staff ({', '.join(names)})", f"{done:.2f}", done)
        beyond = t.step(
            "upkeep beyond them", f"max({total:.2f} − {done:.2f}, 0)", max(total - done, ZERO)
        )
        rest = after_hypercare(t, year)
        if rest != ONE:
            beyond = t.step("after hypercare", f"{beyond:.2f} × {rest:.4f}", beyond * rest)
        if beyond <= ZERO:
            return None
        run = t.calibration("run_multiplier")
        factor = t.step(
            "share priced × run multiplier",
            f"{beyond:.2f} / {total:.2f} × {run}",
            beyond / total * run,
        )
        amount = ZERO
        for role, pd in parts:
            if pd:
                t.add_role_pd(role, pd * factor)
                amount += pd * factor * t.rate_local(role)
        esc = t.escalation("labour", year)
        spreads.clarity(t, clarity)
        spreads.om_year(t, year)
        return t.finish(amount * esc)

    for year in range(1, ctx.q.om_years + 1):
        covered = ZERO  # support work this year that dedicated support staff would do
        if ctx.q.helpdesk_in_scope:
            t = _run(ctx, "helpdesk", "run.helpdesk", year, "Helpdesk", "maintenance.helpdesk.v2")
            users: int = t.driver("users_total")
            if ctx.p.maintenance.helpdesk_seats_points:  # v29+: seats grow with the users
                t.formula_id = "maintenance.helpdesk.v3"
                points: list[Point] = t.param("maintenance", "helpdesk_seats_points")
                seats = t.step(
                    "helpdesk seats",
                    f"interpolate(helpdesk_seats_points, {users})",
                    interpolate(points, Decimal(users)),
                )
            else:
                tiers = ctx.p.maintenance.helpdesk_seats_by_users
                tier = next(
                    i for i, x in enumerate(tiers) if x.max_users is None or users <= x.max_users
                )
                seats = t.param("maintenance", "helpdesk_seats_by_users", tier, "seats")
            sla: str = t.driver("support_sla")
            coverage: Decimal = t.param("maintenance", "helpdesk_coverage_fte", sla)
            t.param("calendar", "pd_per_year")
            pd = t.step(
                "helpdesk person-days",
                f"{seats} × {coverage} × {pd_year}",
                seats * coverage * pd_year,
            )
            line = labour(t, pd, t.param("maintenance", "helpdesk_role"), year)
            lines.append(line)
            if any(r.kind == "support" for r in ctx.q.onsite_resources):
                # only the office-hours part: support staff do not cover nights and holidays
                office = ctx.p.maintenance.helpdesk_coverage_fte[OFFICE_HOURS]
                covered += sum(line.role_pd.values(), ZERO) * office / coverage

        if ctx.p.maintenance.upkeep_one_line:
            upkeep = upkeep_line(year)
            if upkeep is not None:
                lines.append(upkeep)
                covered += sum(upkeep.role_pd.values(), ZERO)
        separate = (
            ("bugfix", "Bug-fix support"),
            ("patching", "Security patching"),
            ("upgrade", "Platform upgrades"),
        )
        for item, label in () if ctx.p.maintenance.upkeep_one_line else separate:
            formula = "maintenance.upgrades.v2" if item == "upgrade" else f"maintenance.{item}.v2"
            t = _run(ctx, item, "run.patching_bugfix", year, label, formula)
            t.follows_build = True
            share: Decimal = t.param("maintenance", f"{item}_share_of_build_pd")
            t.step("build effort", "Σ component effort (pd)", build_effort_pd)
            pd = t.step(
                f"{item} person-days", f"{build_effort_pd:.2f} × {share}", build_effort_pd * share
            )
            line = labour(t, pd, t.param("maintenance", f"{item}_role"), year)
            lines.append(line)
            covered += sum(line.role_pd.values(), ZERO)

        if not ctx.p.maintenance.upkeep_one_line:  # else in the upkeep line
            t = _run(
                ctx,
                "pool",
                "run.change_requests",
                year,
                "Change-request pool",
                "maintenance.change_requests.v2",
            )
            cr: Decimal | None = t.driver("change_request_pd_per_year")
            if cr is None:
                t.follows_build = True
                share = t.param("maintenance", "change_request_share_of_build_pd")
                cr = t.step(
                    "CR person-days", f"{build_effort_pd:.2f} × {share}", build_effort_pd * share
                )
            if cr:
                line = labour(t, cr, t.param("maintenance", "change_request_role"), year)
                lines.append(line)
                covered += sum(line.role_pd.values(), ZERO)

        for i, res in enumerate(ctx.q.onsite_resources):
            if res.days is not None and year > 1:
                continue  # limited onsite days are priced once, in the first support year
            if (
                res.days is None
                and res.months is not None
                and res.months <= MONTHS_A_YEAR * (year - 1)
            ):
                continue  # no longer needed by this support year
            if res.kind == "support":
                staff_line, stated = support_staff_line(res, i, year, covered)
                covered = max(covered - stated, ZERO)
                if staff_line is not None:
                    lines.append(staff_line)
                continue
            if res.days is None:
                formula = "maintenance.onsite.v2" if _v2(res) else "maintenance.onsite.v1"
            else:
                formula = "maintenance.onsite_days.v1"
            t = _run(
                ctx,
                f"onsite{i}",
                "run.onsite_resources",
                year,
                staff_label(res, f"Onsite {res.role.removeprefix('role.')}"),
                formula,
            )
            t.driver("onsite_resources")
            if res.days is None:
                pd = staff_pd(t, res, year, "onsite")
            else:
                pd = t.step("onsite person-days", f"{res.count} × {res.days}", res.count * res.days)
            lines.append(labour(t, pd, res.role, year, scaled=False))

        t = _run(
            ctx,
            "audit",
            "run.annual_audit",
            year,
            "Annual security re-audit",
            "maintenance.annual_audit.v1",
        )
        first: int = ctx.p.maintenance.annual_audit_from_year
        if first > 1 and year < first and ctx.q.cert_in_audit:
            t.param("maintenance", "annual_audit_from_year")  # the go-live audit is this year's
        elif t.driver("cert_in_audit"):
            prefix: str = t.param("maintenance", "annual_audit_rate_prefix")
            lines.append(price(t, band_fee(t, build_effort_pd, prefix), year))

        t = _run(
            ctx,
            "ssl_domain",
            "run.ssl_domain",
            year,
            "SSL certificate and domain",
            "maintenance.ssl_domain.v1",
        )
        lines.append(price(t, _ssl_and_domain(t), year))

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
                lines.append(price(t, t.rate_local(key), year))
    return lines

"""Infrastructure sizing -> priced hosting line items (brief 7.4).

From users, peak concurrency, document volume and uptime SLA this picks an architecture
pattern (single / HA / HA + DR), sizes app servers, database tier and storage per year, and
prices them from the rate card for AWS, a MeitY-empanelled Indian cloud or on-prem.
Pure functions: no database, no LLM.
"""

from dataclasses import dataclass
from decimal import Decimal

from app.services.engine import spreads
from app.services.engine.components import concurrency_band_index
from app.services.engine.context import LineBuilder, PricingContext
from app.services.engine.money import ONE, ZERO, ceil
from app.services.engine.outputs import CostLineOut


@dataclass(frozen=True)
class HostingPlan:
    pattern: str
    app_servers: Decimal
    db_tier: str
    db_instances: Decimal
    transfer_gb_month: Decimal
    server_rate: str = "app_server"  # or "app_server_small" (rate card item suffix)
    small_site: bool = False  # the database runs on the one small server (parameter sets v25+)


def size(t: LineBuilder) -> HostingPlan:
    """pattern = pattern_by_sla[sla], or ha_dr when a disaster-recovery site is asked for
    app_servers = max(min_servers[pattern], ceil(ceil(peak / users_per_vcpu) / vcpu_per_server))
    server rate = small server when ceil(peak / users_per_vcpu) ≤ small_app_server_max_vcpus
                  and the rate card prices one (parameter sets v12+), else the standard server
    db_tier from the concurrency band; db_instances[pattern]
    transfer_gb_month = users × monthly_active_share × mb_per_active_user_month / mb_per_gb
    small site (parameter sets v25+) = pattern single on the small server rate: the database
                  runs on that server, db_instances = 0
    """
    pattern = _pattern(t)
    peak: int = t.driver("peak_concurrent_users")
    per_vcpu: Decimal = t.param("hosting", "concurrent_users_per_vcpu")
    per_server: Decimal = t.param("hosting", "vcpu_per_app_server")
    min_servers: Decimal = t.param("hosting", "min_app_servers", pattern)
    vcpus = ceil(Decimal(peak) / per_vcpu)
    servers = t.step(
        "app servers",
        f"max({min_servers}, ceil(ceil({peak} / {per_vcpu}) / {per_server}))",
        max(min_servers, ceil(vcpus / per_server)),
    )
    band = concurrency_band_index(t.ctx, peak)
    db_tier: str = t.param("nfr", "concurrency_bands", band, "db_tier")
    db_instances: Decimal = t.param("hosting", "db_instances", pattern)
    users: int = t.driver("users_total")
    active: Decimal = t.param("hosting", "monthly_active_share")
    mb_user: Decimal = t.param("hosting", "transfer_mb_per_active_user_month")
    mb_gb: Decimal = t.param("hosting", "mb_per_gb")
    transfer = t.step(
        "transfer GB / month",
        f"{users} × {active} × {mb_user} / {mb_gb}",
        users * active * mb_user / mb_gb,
    )
    server_rate = "app_server"
    small_max = t.ctx.p.hosting.small_app_server_max_vcpus
    provider = t.ctx.q.hosting_provider
    small_key = f"cloud.{provider}.app_server_small.month"
    if small_max is not None and small_key in t.ctx.rates:
        limit: Decimal = t.param("hosting", "small_app_server_max_vcpus")
        if vcpus <= limit:
            server_rate = "app_server_small"
            t.step("small servers", f"ceil({peak} / {per_vcpu}) = {vcpus} ≤ {limit} vCPUs", vcpus)
    small_site = (
        t.ctx.p.hosting.small_site is not None
        and pattern == "single"
        and server_rate == "app_server_small"
    )
    if small_site:
        t.param("hosting", "small_site", "source")
        db_instances = t.step("database instances", "on the one small server (small site)", ZERO)
    t.add_input(pattern=pattern, app_servers=str(servers), db_tier=db_tier, server=server_rate)
    return HostingPlan(pattern, servers, db_tier, db_instances, transfer, server_rate, small_site)


def free_monitoring(t: LineBuilder, plan: HostingPlan) -> bool:
    """A small site on a provider whose free monitoring tier covers it (parameter sets v25+)."""
    rule = t.ctx.p.hosting.small_site
    if not plan.small_site or rule is None:
        return False
    free: list[str] = t.param("hosting", "small_site", "monitoring_free_providers")
    return t.ctx.q.hosting_provider in free


def _pattern(t: LineBuilder) -> str:
    """pattern = pattern_by_sla[sla], or ha_dr when a disaster-recovery site is asked for."""
    sla = t.driver("uptime_sla")
    pattern: str = t.param("hosting", "pattern_by_sla", sla)
    if t.ctx.q.disaster_recovery and pattern != "ha_dr":
        # a standby site is its own requirement, not implied by high uptime (v17+ maps no
        # uptime level to ha_dr)
        t.driver("disaster_recovery")
        pattern = "ha_dr"
    return pattern


def _discount(t: LineBuilder) -> Decimal:
    """1 − reserved_discount[provider] with reserved pricing, else 1."""
    if t.driver("hosting_pricing") == "reserved":
        d: Decimal = t.param("hosting", "reserved_discount", t.ctx.q.hosting_provider)
        return t.step("reserved discount", f"1 − {d}", ONE - d)
    return ONE


def bundle_key(ctx: PricingContext, pattern: str, band: str) -> str:
    return f"hosting.{ctx.q.hosting_provider}.{pattern}.{band}.month"


def _bundled(ctx: PricingContext) -> bool:
    """Hosting as one line (parameter sets v25+ with a rate card that prices it, v10+)."""
    return ctx.p.hosting.bundle is not None and bundle_key(ctx, "single", "low") in ctx.rates


def _bundle_lines(ctx: PricingContext) -> list[CostLineOut]:
    """hosting.bundle.v1 (parameter sets v25+), one line a year:
    hosting_year = month_rate[provider, pattern, band] × discount × months_per_year
                   × (1 + escalation_prices)^year
    month_rate is the whole set-up (servers, database, load balancer, monitoring, storage,
    backups, transfer, DR) at the middle of the load band (rate card v10); pattern as `size`;
    band = the concurrency band of the peak users online at once. The load within the band
    is the line's own spread: band_spread[provider][pattern][band], plus the hosting spread."""
    lines: list[CostLineOut] = []
    provider = ctx.q.hosting_provider
    months = ctx.months_per_year()
    for year in range(1, ctx.q.om_years + 1):
        t = _base(
            ctx,
            "bundle",
            "run.hosting",
            year,
            f"Hosting: servers, database, storage, backups and monitoring (year {year})",
            "hosting.bundle.v1",
        )
        t.driver("om_years")
        pattern = _pattern(t)
        peak: int = t.driver("peak_concurrent_users")
        index = concurrency_band_index(ctx, peak)
        band: str = t.param("nfr", "concurrency_bands", index, "name")
        rate = t.rate_local(bundle_key(ctx, pattern, band))
        annual = t.step(
            "hosting per year", "month rate × discount × months", rate * _discount(t) * months
        )
        spread = t.param("hosting", "bundle", "band_spread", provider, pattern, band)
        t.spread(f"load within the {band} band", spread.down, spread.up)
        t.add_input(pattern=pattern, band=band)
        esc = t.escalation("prices", year)
        spreads.fixed(t, "hosting")
        spreads.om_year(t, year)
        lines.append(t.finish(annual * esc))
    return lines


def storage_gb(t: LineBuilder, year: int) -> Decimal:
    """storage_gb(year) = base + db
    + documents_per_month × months_per_year × year × avg_mb / mb_per_gb"""
    base: Decimal = t.param("hosting", "base_storage_gb")
    db: Decimal = t.param("hosting", "db_storage_gb")
    docs: int = t.driver("documents_per_month")
    avg_mb: Decimal = t.driver("avg_document_mb")
    mb_gb: Decimal = t.param("hosting", "mb_per_gb")
    months = t.ctx.months_per_year()
    return t.step(
        f"storage GB (end of year {year})",
        f"{base} + {db} + {docs} × {months} × {year} × {avg_mb} / {mb_gb}",
        base + db + docs * months * year * avg_mb / mb_gb,
    )


def _base(
    ctx: PricingContext, item: str, bucket: str, year: int, label: str, formula: str
) -> LineBuilder:
    t = ctx.builder(
        line_key=f"{bucket}/{item}/y{year}",
        stage="go_live" if year == 0 else "run",
        bucket=bucket,
        year=year,
        label=label,
        formula_id=formula,
    )
    t.driver("hosting_provider")
    return t


def hosting_lines(ctx: PricingContext) -> list[CostLineOut]:
    if not ctx.q.hosting_in_scope:  # the client provides hosting: nothing to price
        return []
    if ctx.q.hosting_provider == "on_prem":
        return _on_prem_lines(ctx)
    if _bundled(ctx):
        return _bundle_lines(ctx)
    return _cloud_lines(ctx)


def _cloud_lines(ctx: PricingContext) -> list[CostLineOut]:
    lines: list[CostLineOut] = []
    provider = ctx.q.hosting_provider
    prefix = f"cloud.{provider}"
    months = ctx.months_per_year()
    for year in range(1, ctx.q.om_years + 1):

        def line(item: str, bucket: str, label: str, formula: str, y: int = year) -> LineBuilder:
            t = _base(ctx, item, bucket, y, f"{label} (year {y})", formula)
            t.driver("om_years")
            return t

        def discount(t: LineBuilder) -> Decimal:
            if t.driver("hosting_pricing") == "reserved":
                d: Decimal = t.param("hosting", "reserved_discount", provider)
                return t.step("reserved discount", f"1 − {d}", ONE - d)
            return ONE

        def finish(t: LineBuilder, annual: Decimal, y: int = year) -> CostLineOut:
            esc = t.escalation("prices", y)
            spreads.fixed(t, "hosting")
            spreads.om_year(t, y)
            return t.finish(annual * esc)

        t = line("compute", "run.hosting", "Application servers", "hosting.compute.v1")
        plan = size(t)
        compute = (
            plan.app_servers
            * t.rate_local(f"{prefix}.{plan.server_rate}.month")
            * discount(t)
            * months
        )
        t.step("compute per year", "servers × rate × discount × months", compute)
        lines.append(finish(t, compute))

        t = line("database", "run.hosting", "Managed database", "hosting.database.v1")
        plan = size(t)
        if plan.small_site:  # the database runs on the app server: no line
            database = ZERO
        else:
            database = (
                plan.db_instances
                * t.rate_local(f"{prefix}.db.{plan.db_tier}.month")
                * discount(t)
                * months
            )
            t.step("database per year", "instances × rate × discount × months", database)
            lines.append(finish(t, database))

        t = line("storage", "run.hosting", "Object and block storage", "hosting.storage.v1")
        gb = storage_gb(t, year)
        lines.append(finish(t, gb * t.rate_local(f"{prefix}.storage.gb_month") * months))

        t = line("backup", "run.backups", "Backups", "hosting.backup.v1")
        gb = storage_gb(t, year) * t.param("hosting", "backup_factor")
        lines.append(finish(t, gb * t.rate_local(f"{prefix}.backup.gb_month") * months))

        t = line("transfer", "run.hosting", "Data transfer out", "hosting.transfer.v1")
        plan = size(t)
        lines.append(
            finish(t, plan.transfer_gb_month * t.rate_local(f"{prefix}.transfer_out.gb") * months)
        )

        t = line("monitoring", "run.hosting", "Monitoring and logging", "hosting.monitoring.v1")
        # only v25+ sizes here, so older estimates keep their trace (rule 3)
        small = ctx.p.hosting.small_site is not None
        if not (small and free_monitoring(t, size(t))):
            lines.append(finish(t, t.rate_local(f"{prefix}.monitoring.month") * months))

        if plan.pattern != "single":
            t = line("load_balancer", "run.hosting", "Load balancer", "hosting.load_balancer.v1")
            size(t)
            lines.append(finish(t, t.rate_local(f"{prefix}.load_balancer.month") * months))

        if plan.pattern == "ha_dr":
            t = line("dr", "run.dr", "Disaster recovery (warm standby)", "hosting.dr.v1")
            size(t)
            factor: Decimal = t.param("hosting", "dr_cost_factor")
            dr = t.step(
                "DR per year",
                f"{factor} × ({compute:.2f} + {database:.2f})",
                factor * (compute + database),
            )
            lines.append(finish(t, dr))
    return lines


def _on_prem_lines(ctx: PricingContext) -> list[CostLineOut]:
    lines: list[CostLineOut] = []
    t = _base(
        ctx,
        "capex",
        "go_live.infrastructure_procurement",
        0,
        "On-prem servers and storage (capex)",
        "golive.onprem_capex.v1",
    )
    t.driver("om_years")
    plan = size(t)
    servers = plan.app_servers + plan.db_instances
    if plan.pattern == "ha_dr":
        factor: Decimal = t.param("hosting", "dr_cost_factor")
        servers += ceil(servers * factor)
    servers = t.step("servers", "app + db (+ DR share)", servers)
    gb = storage_gb(t, ctx.q.om_years) * (ONE + t.param("hosting", "backup_factor"))
    tb = t.step(
        "storage TB", f"ceil({gb:.2f} / gb_per_tb)", ceil(gb / t.param("hosting", "gb_per_tb"))
    )
    capex = servers * t.rate_local(
        t.param("hosting", "on_prem", "server_rate_key")
    ) + tb * t.rate_local(t.param("hosting", "on_prem", "storage_tb_rate_key"))
    spreads.fixed(t, "hosting")
    lines.append(t.finish(capex))

    months = ctx.months_per_year()
    for year in range(1, ctx.q.om_years + 1):
        c = _base(
            ctx,
            "colocation",
            "run.hosting",
            year,
            f"Data-centre colocation (year {year})",
            "hosting.onprem_colocation.v1",
        )
        c.driver("om_years")
        per_rack: Decimal = c.param("hosting", "on_prem", "servers_per_rack")
        racks = c.step("racks", f"ceil({servers} / {per_rack})", ceil(servers / per_rack))
        coloc = racks * c.rate_local(c.param("hosting", "on_prem", "colocation_rate_key")) * months
        esc = c.escalation("prices", year)
        spreads.fixed(c, "hosting")
        spreads.om_year(c, year)
        lines.append(c.finish(coloc * esc))

        a = _base(
            ctx, "amc", "run.hosting", year, f"Hardware AMC (year {year})", "hosting.onprem_amc.v1"
        )
        a.driver("om_years")
        amc: Decimal = a.param("hosting", "on_prem", "hw_amc_percent")
        a.step("capex", "servers × server_capex + TB × tb_capex", capex)
        esc = a.escalation("prices", year)
        spreads.fixed(a, "hosting")
        spreads.om_year(a, year)
        lines.append(a.finish(amc * capex * esc))
    return [line for line in lines if line.likely_paise > ZERO]

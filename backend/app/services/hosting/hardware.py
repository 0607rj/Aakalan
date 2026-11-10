"""The hardware list for own servers (parameter sets v35+, formula hardware_list.v1,
OPEN_QUESTIONS 231): what to buy, how many and of what size.

Quantities come from the same sizing as the cloud servers (hosting/sizing.size): the people
online at once set the application servers, the concurrency band the database server, the
uptime the pattern (single / two of each / two of each and a standby site), the documents and
years the storage. Per site:

  application servers = app_servers  (one server for the application and database on a small site)
  database servers    = db_instances
  storage TB          = ceil(storage_gb(om_years) × (1 + backup_factor) / gb_per_tb)
  firewall, switch    = 2 when the pattern is in paired_for, else 1
  load balancer       = as the firewall, when the servers users reach ≥ load_balancer_min_servers
  backup              = 1 at the main site
  racks with UPS      = ceil(servers / servers_per_rack)
  operating system, antivirus = one per server; database licence = one per database server
                        when licensing is "licensed"
  standby site (ha_dr) = ceil(servers × dr_cost_factor), the same storage, one firewall and
                        one switch

Parameter sets v37+ (OPEN_QUESTIONS 233): application and database share servers while one
server of shared_host_cores holds both (application cores per server + the database's cores);
each item is priced from the rate card (servers by size: server_rate_by_cores, the smallest size
with at least the cores asked; storage per TB; subscriptions per year), and with own servers in
the price the hosting lines are this list (`on_prem_lines`: formulas golive.onprem_capex.v2,
hosting.onprem_amc.v1, hosting.onprem_subscriptions.v1).

Shown when the client runs its own servers (hosting_provider on_prem) or asks for it
(hardware_list client_buys: priced for information, not in the price). Pure: no database, no
LLM; the same inputs give the same list."""

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, computed_field

from app.services.engine import spreads
from app.services.engine.context import LineBuilder, PricingContext
from app.services.engine.inputs import EstimateInput
from app.services.engine.money import ONE, ZERO, ceil, to_paise
from app.services.engine.outputs import CostLineOut
from app.services.engine.reference import Hardware
from app.services.hosting.sizing import size, storage_gb

FORMULA_ID = "hardware_list.v1"
CAPEX_FORMULA = "golive.onprem_capex.v2"
SUBSCRIPTIONS_FORMULA = "hosting.onprem_subscriptions.v1"
SERVERS = ("app_server", "db_server", "single_server")

Site = Literal["main", "standby"]


class HardwareItem(BaseModel):
    key: str
    label: str
    spec: str
    quantity: int
    site: Site
    why: str
    source: Literal["sized", "document"] = "sized"  # sized = worked out here (our estimate)
    # v37+: the price of one (paise; storage: per TB), from rate_keys; None = not priced
    unit_paise: int | None = None
    yearly: bool = False  # a subscription paid each year
    rate_keys: list[str] = []
    tb: int | None = None  # storage: the TB priced

    @computed_field  # type: ignore[prop-decorator]
    @property
    def amount_paise(self) -> int:  # quantity × (TB) × price of one; 0 = free or not priced
        return (self.unit_paise or 0) * self.quantity * (self.tb or 1)


class HardwareList(BaseModel):
    who_buys: Literal["in_price", "client_buys"]
    parameter_set_version: str
    source: str  # the parameter group's source
    items: list[HardwareItem]
    client_costs: list[str] = []  # own building: costs the client pays itself (not priced)
    once_paise: int | None = None  # v37+: buying it all (one-time items, before tax)
    yearly_paise: int | None = None  # v37+: subscriptions each year (before escalation, tax)


def _whole(value: Decimal) -> int:
    return int(ceil(value))


def wanted(ctx: PricingContext) -> Literal["in_price", "client_buys"] | None:
    if ctx.p.hardware is None:
        return None
    if ctx.q.hosting_provider == "on_prem" and ctx.q.hosting_in_scope:
        # the client may buy the hardware itself (question hardware_supply, OPEN_QUESTIONS 235)
        return "client_buys" if ctx.q.hardware_list == "client_buys" else "in_price"
    if ctx.q.hardware_list == "client_buys":
        return "client_buys"
    return None


def hardware_list(inp: EstimateInput) -> HardwareList | None:
    """The list for an estimate's inputs, or None when it has none (see `wanted`)."""
    ctx = PricingContext(inp)
    who = wanted(ctx)
    hw = ctx.p.hardware
    if who is None or hw is None:
        return None
    t = ctx.builder(
        line_key="hardware",
        stage="go_live",
        bucket="go_live.infrastructure_procurement",
        year=0,
        label="Hardware list",
        formula_id=FORMULA_ID,
    )
    items = _items(t, hw)
    priced = hw.priced
    return HardwareList(
        who_buys=who,
        parameter_set_version=ctx.p.version,
        source=hw.source,
        items=items,
        client_costs=hw.own_room_costs
        if ctx.q.hosting_provider == "on_prem" and not ctx.p.hosting.on_prem.rent_racks
        else [],
        once_paise=sum(i.amount_paise for i in items if not i.yearly) if priced else None,
        yearly_paise=sum(i.amount_paise for i in items if i.yearly) if priced else None,
    )


def _server_key(hw: Hardware, cores: int) -> str:
    """The smallest server size on the rate card with at least `cores`, else the largest."""
    sizes = sorted(hw.server_rate_by_cores)
    return hw.server_rate_by_cores[next((s for s in sizes if s >= cores), sizes[-1])]


def _items(t: LineBuilder, hw: Hardware) -> list[HardwareItem]:
    q = t.ctx.q
    plan = size(t)
    peak = q.peak_concurrent_users
    load = f"about {peak:,} people online at once, {q.uptime_sla}% uptime: " + hw.pattern_words.get(
        plan.pattern, plan.pattern
    )
    per_vcpu: Decimal = t.param("hosting", "vcpu_per_app_server")
    cores = max(hw.app_server_min_cores, int(per_vcpu))
    disk = hw.app_server_disk
    words = hw.items
    out: list[HardwareItem] = []

    def add(key: str, qty: int, why: str, site: Site = "main", **fmt: object) -> None:
        if qty <= 0:
            return
        w = words[key]
        licensed = key == "os" and q.licensing == "licensed"
        spec = (w.spec_licensed if licensed else None) or w.spec
        keys: list[str] = []
        if hw.priced:
            keys = list(w.rate_keys_licensed if licensed else w.rate_keys)
            if key in SERVERS:
                keys = [_server_key(hw, int(str(fmt["cores"])))]
        unit = to_paise(sum((t.rate_local(k) for k in keys), ZERO)) if keys else None
        tb = int(str(fmt["tb"])) if w.per_tb and "tb" in fmt else None
        out.append(
            HardwareItem(
                key=key, label=w.label, spec=spec.format(**fmt), quantity=qty, site=site,
                why=why, unit_paise=unit, yearly=w.yearly, rate_keys=keys, tb=tb,
            )
        )  # fmt: skip

    app = _whole(plan.app_servers)
    db = _whole(plan.db_instances)
    db_spec = hw.db_servers[plan.db_tier]
    host = hw.shared_host_cores
    shared = (
        host is not None
        and not plan.small_site
        and db > 0
        and app <= db
        and int(per_vcpu) + db_spec.cores <= host
    )
    if shared and host is not None:  # v37+: application and database on the same servers
        why = f"{load}; the application and its database share each server"
        add("single_server", db, why, cores=host, ram=host * hw.ram_gb_per_core,
            disk=hw.db_server_disk)  # fmt: skip
        app, servers = 0, db
    elif plan.small_site:
        add("single_server", app, load, cores=cores, ram=cores * hw.ram_gb_per_core, disk=disk)
        servers = app
    else:
        add("app_server", app, load, cores=cores, ram=cores * hw.ram_gb_per_core, disk=disk)
        add("db_server", db, f"database for {load}", cores=db_spec.cores, ram=db_spec.ram_gb,
            disk=hw.db_server_disk)  # fmt: skip
        servers = app + db
    front = app or servers  # the servers the users reach
    gb = storage_gb(t, q.om_years) * (ONE + t.param("hosting", "backup_factor"))
    tb = max(1, _whole(gb / t.param("hosting", "gb_per_tb")))
    years = "1 year" if q.om_years == 1 else f"{q.om_years} years"
    data = f"{q.documents_per_month:,} documents a month for {years}, with backups"
    add("storage", 1, data, tb=tb)
    add("backup", 1, "a copy of the data off the main storage")
    pair = 2 if plan.pattern in hw.paired_for else 1
    two = "two, so one can fail" if pair == 2 else "one site, one device"
    add("firewall", pair, two)
    if "firewall_security" in words:  # v37: the firewall's yearly security subscription
        add("firewall_security", pair, "one per firewall")
    add("switch", pair, two)
    if front >= hw.load_balancer_min_servers:
        add("load_balancer", pair, f"{front} servers share the users")
    per_rack: Decimal = t.param("hosting", "on_prem", "servers_per_rack")
    add("rack", _whole(Decimal(servers) / per_rack), f"{servers} servers")
    add("os", servers, "one per server")
    if q.licensing == "licensed":
        add("database_licence", db or servers, "a licensed database was asked for")
    add("antivirus", servers, "one per server")

    if plan.pattern == "ha_dr":
        share: Decimal = t.param("hosting", "dr_cost_factor")
        standby = "standby site, takes over if the main site fails"
        if shared and host is not None:
            s_servers = _whole(servers * share)
            add("single_server", s_servers, standby, "standby", cores=host,
                ram=host * hw.ram_gb_per_core, disk=hw.db_server_disk)  # fmt: skip
        else:
            s_app = _whole(app * share)
            s_db = _whole(db * share)
            add("app_server", s_app, standby, "standby", cores=cores,
                ram=cores * hw.ram_gb_per_core, disk=disk)  # fmt: skip
            if db:
                add("db_server", s_db, standby, "standby", cores=db_spec.cores,
                    ram=db_spec.ram_gb, disk=hw.db_server_disk)  # fmt: skip
            s_servers = s_app + s_db
        add("storage", 1, standby, "standby", tb=tb)
        add("firewall", 1, standby, "standby")
        if "firewall_security" in words:
            add("firewall_security", 1, standby, "standby")
        add("switch", 1, standby, "standby")
        add("rack", _whole(Decimal(s_servers) / per_rack), standby, "standby")
        add("os", s_servers, standby, "standby")
        add("antivirus", s_servers, standby, "standby")
    return out


def on_prem_lines(ctx: PricingContext) -> list[CostLineOut]:
    """Own servers in the price, from the hardware list (parameter sets v37+, OPEN_QUESTIONS
    233):

      buying = Σ one-time items: quantity × (TB) × unit price           (golive.onprem_capex.v2)
      year y AMC = hw_amc_percent × buying × escalation(prices, y)       (hosting.onprem_amc.v1)
      year y subscriptions = Σ yearly items: quantity × unit price × escalation(prices, y)
                                                               (hosting.onprem_subscriptions.v1)
    No rack rent in the client's own building (rent_racks false, v36+)."""
    hw = ctx.p.hardware
    assert hw is not None and hw.priced
    t = ctx.builder(
        line_key="go_live.infrastructure_procurement/capex/y0",
        stage="go_live",
        bucket="go_live.infrastructure_procurement",
        year=0,
        label="Own servers, storage and network (buying)",
        formula_id=CAPEX_FORMULA,
    )
    t.driver("hosting_provider")
    t.driver("om_years")
    t.param("hardware", "server_rate_by_cores")
    items = _items(t, hw)
    capex = ZERO
    for i in items:
        if i.yearly or not i.unit_paise:
            continue
        unit = Decimal(i.unit_paise) / 100
        per = f" × {i.tb} TB" if i.tb else ""
        capex += t.step(
            f"{i.label} ({i.site})", f"{i.quantity}{per} × ₹{unit}",
            unit * i.quantity * (i.tb or 1),
        )  # fmt: skip
    spreads.fixed(t, "hosting")
    lines = [t.finish(capex)]
    yearly = [i for i in items if i.yearly and i.unit_paise]
    for year in range(1, ctx.q.om_years + 1):
        a = ctx.builder(
            line_key=f"run.hosting/amc/y{year}",
            stage="run",
            bucket="run.hosting",
            year=year,
            label=f"Hardware repairs and warranty, AMC (year {year})",
            formula_id="hosting.onprem_amc.v1",
        )
        a.driver("hosting_provider")
        a.driver("om_years")
        amc: Decimal = a.param("hosting", "on_prem", "hw_amc_percent")
        a.step("buying", "Σ items × unit price", capex)
        esc = a.escalation("prices", year)
        spreads.fixed(a, "hosting")
        spreads.om_year(a, year)
        lines.append(a.finish(amc * capex * esc))
        if not yearly:
            continue
        s = ctx.builder(
            line_key=f"run.hosting/subscriptions/y{year}",
            stage="run",
            bucket="run.hosting",
            year=year,
            label=f"Software licences and subscriptions (year {year})",
            formula_id=SUBSCRIPTIONS_FORMULA,
        )
        s.driver("hosting_provider")
        total = ZERO
        for i in yearly:
            for k in i.rate_keys:
                s.rate(k)  # the trace names every price
            unit = Decimal(i.unit_paise or 0) / 100
            total += s.step(f"{i.label} ({i.site})", f"{i.quantity} × ₹{unit}", unit * i.quantity)
        esc = s.escalation("prices", year)
        spreads.fixed(s, "hosting")
        spreads.om_year(s, year)
        lines.append(s.finish(total * esc))
    return [line for line in lines if line.likely_paise > ZERO]

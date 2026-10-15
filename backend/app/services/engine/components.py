"""Component labour cost (brief 7.1)."""

from dataclasses import dataclass
from decimal import Decimal

from app.services.engine import spreads
from app.services.engine.context import LineBuilder, PricingContext
from app.services.engine.inputs import ComponentInstanceIn
from app.services.engine.money import ONE, ZERO, dsum
from app.services.engine.outputs import CostLineOut
from app.services.engine.reference import CatalogComponent, Driver, Size, TaskType


@dataclass(frozen=True)
class ComponentEffort:
    instance: ComponentInstanceIn
    catalog: CatalogComponent
    effort_pd: Decimal  # before schedule compression


def concurrency_band_index(ctx: PricingContext, peak_users: int) -> int:
    for i, band in enumerate(ctx.p.nfr.concurrency_bands):
        if band.max_peak_users is None or peak_users <= band.max_peak_users:
            return i
    raise ValueError("concurrency_bands must end with an open-ended band")


def nfr_multiplier(t: LineBuilder, catalog: CatalogComponent) -> Decimal:
    """M_nfr = Π over the component's applicable drivers of the driver's multiplier.

    languages: min(cap, 1 + per_additional_language × (languages − 1)).
    """
    m = ONE
    for drv in catalog.applicable_drivers:
        if drv is Driver.UPTIME_SLA:
            factor: Decimal = t.param("nfr", "uptime_sla", t.driver("uptime_sla"))
        elif drv is Driver.SECURITY_LEVEL:
            factor = t.param("nfr", "security_level", t.driver("security_level"))
        elif drv is Driver.LANGUAGES:
            extra: Decimal = t.param("nfr", "per_additional_language")
            cap: Decimal = t.param("nfr", "languages_cap")
            factor = min(cap, ONE + extra * (t.driver("languages") - 1))
        elif drv is Driver.ACCESSIBILITY:
            flag = "true" if t.driver("gigw_accessibility") else "false"
            factor = t.param("nfr", "accessibility", flag)
        else:
            idx = concurrency_band_index(t.ctx, t.driver("peak_concurrent_users"))
            factor = t.param("nfr", "concurrency_bands", idx, "multiplier")
        m *= factor
    return t.step("M_nfr", " × ".join(d.value for d in catalog.applicable_drivers) or "1", m)


def _uses_licence(ctx: PricingContext, catalog: CatalogComponent) -> bool:
    return catalog.licence is not None and ctx.q.licensing == "licensed"


def base_effort(ctx: PricingContext, ci: ComponentInstanceIn) -> ComponentEffort:
    """Effort in person-days before compression (used to size the timeline).

    effort = Σ_task base_pd[size] × quantity × share × M_complexity × M_nfr × licence_factor
             × (1 − min(max_saving, saving_task × maturity_scale))
    """
    catalog = ctx.inp.catalog.get(ci.catalog_key)
    scratch = ctx.builder(
        line_key="scratch",
        stage="build",
        bucket=catalog.bucket,
        year=0,
        label="",
        formula_id="component_labour.v1",
    )
    per_task = _task_efforts(scratch, ci, catalog)
    return ComponentEffort(ci, catalog, dsum(per_task.values()))


def _task_efforts(
    t: LineBuilder, ci: ComponentInstanceIn, catalog: CatalogComponent
) -> dict[TaskType, Decimal]:
    base: Decimal = catalog.base_effort_pd[Size(ci.size)]
    m_cx: Decimal = t.param("complexity_multipliers", ci.complexity.value)
    m_nfr = nfr_multiplier(t, catalog)
    lic = ONE
    if _uses_licence(t.ctx, catalog) and catalog.licence is not None:
        t.driver("licensing")
        lic = catalog.licence.effort_factor
    maturity = t.driver("team_ai_maturity")
    scale: Decimal = t.param("ai_productivity", "maturity_scale", maturity)
    cap: Decimal = t.param("ai_productivity", "max_saving")
    efforts: dict[TaskType, Decimal] = {}
    for task, share in catalog.task_mix.items():
        saving: Decimal = t.param("ai_productivity", "task_savings", task.value)
        effective_saving = min(cap, saving * scale)
        efforts[task] = base * ci.quantity * share * m_cx * m_nfr * lic * (ONE - effective_saving)
    return efforts


def component_line(
    ctx: PricingContext, effort: ComponentEffort, compression: Decimal
) -> CostLineOut:
    """Price one component instance; the line carries per-task steps and role person-days."""
    ci, catalog = effort.instance, effort.catalog
    stage = catalog.bucket.split(".", 1)[0]
    t = ctx.builder(
        line_key=f"{catalog.bucket}/{ci.id}",
        stage=stage,
        bucket=catalog.bucket,
        year=0,
        label=ci.label or catalog.name,
        formula_id="component_labour.v1",
        uncertainty_group=f"{catalog.bucket}|{ci.id}",
    )
    t.link_component(ci, catalog)
    t.add_input(
        size=ci.size.value,
        complexity=ci.complexity.value,
        quantity=ci.quantity,
        base_effort_pd=str(catalog.base_effort_pd[Size(ci.size)]),
        compression_multiplier=str(compression),
    )
    efforts = _task_efforts(t, ci, catalog)
    total = ZERO
    for task, pd in efforts.items():
        role_key: str = t.param("task_roles", "roles", task.value)
        rate = t.rate_inr(role_key)
        pd_c = pd * compression
        cost = t.step(
            f"{task.value} → {role_key}",
            f"{pd:.4f} pd × compression {compression:.4f} × ₹{rate}/pd",
            pd_c * rate,
        )
        t.add_role_pd(role_key, pd_c)
        total += cost
    t.add_input(effort_pd=str(dsum(efforts.values()) * compression))
    spreads.clarity(t, ctx.component_clarity(ci))
    spreads.template_match(t)
    spreads.tags(t, list(catalog.tags))
    spreads.compression(t, compression)
    return t.finish(total)

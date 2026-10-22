"""Component labour cost (brief 7.1)."""

from dataclasses import dataclass
from decimal import Decimal

from app.services.engine import spreads
from app.services.engine.context import LineBuilder, PricingContext
from app.services.engine.inputs import ComponentInstanceIn
from app.services.engine.money import ONE, ZERO, dsum
from app.services.engine.outputs import CostLineOut
from app.services.engine.reference import BaselineEra, CatalogComponent, Driver, Size, TaskType


@dataclass(frozen=True)
class ComponentEffort:
    instance: ComponentInstanceIn
    catalog: CatalogComponent
    effort_pd: Decimal  # before schedule compression
    ai_saved_pd: Decimal = ZERO  # effort the team's AI tools save (before compression)


def concurrency_band_index(ctx: PricingContext, peak_users: int) -> int:
    for i, band in enumerate(ctx.p.nfr.concurrency_bands):
        if band.max_peak_users is None or peak_users <= band.max_peak_users:
            return i
    raise ValueError("concurrency_bands must end with an open-ended band")


def nfr_multiplier(t: LineBuilder, catalog: CatalogComponent) -> Decimal:
    """M_nfr = Π over the component's applicable drivers of the driver's multiplier.

    languages: min(cap, 1 + per_additional_language × (languages − 1)).
    accessibility: 1 when the project has a component that builds accessibility as its own work
    (nfr.accessibility_components, v17+), so the same work is not priced twice; languages: the
    same with nfr.languages_components (v19+).
    """
    m = ONE
    in_project = {c.catalog_key for c in t.ctx.inp.components}
    drivers = list(catalog.applicable_drivers)
    for driver, field in (
        (Driver.ACCESSIBILITY, "accessibility_components"),
        (Driver.LANGUAGES, "languages_components"),
    ):
        dedicated: list[str] = getattr(t.ctx.p.nfr, field)
        if driver in drivers and in_project & set(dedicated):
            t.param("nfr", field)
            drivers.remove(driver)
    for drv in drivers:
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
    return t.step("M_nfr", " × ".join(d.value for d in drivers) or "1", m)


def _uses_licence(ctx: PricingContext, catalog: CatalogComponent) -> bool:
    return catalog.licence is not None and ctx.q.licensing == "licensed"


def ai_saving_applies(ctx: PricingContext, catalog: CatalogComponent) -> bool:
    """Whether the team's AI savings may reduce this component's effort, so they are applied
    at most once:

      no era recorded (catalogs v1-v5) → yes, as before
      pre_ai                           → yes
      ai_assisted                      → never (the observed hours already include AI tools)
      unknown                          → yes when ai_productivity.unknown_era_is_pre_ai
                                         (v18+: the hours are calibrated against pre-AI
                                         projects); else only in the pre-AI sensitivity run
                                         (EstimateInput.era_scenario)
    """
    era = catalog.source_era
    if era is None or era is BaselineEra.PRE_AI:
        return True
    if era is BaselineEra.AI_ASSISTED:
        return False
    return ctx.p.ai_productivity.unknown_era_is_pre_ai or (
        ctx.inp.era_scenario == "pre_ai_sensitivity"
    )


def reuse_multiplier(t: LineBuilder, ci: ComponentInstanceIn) -> tuple[set[TaskType], Decimal]:
    """(task types it applies to, M_reuse) for what the build reuses (parameter sets v19+):

      M_reuse = reuse.factor_by_build_type[build_type] on the reuse.tasks shares only

    No reuse factors in the set, none for this build type (custom, ready_product), or a
    component that holds a hard problem (a CMS does not solve it): 1.
    """
    reuse = t.ctx.p.reuse
    if reuse is None or ci.hard_problem:
        return set(), ONE
    build: str = t.driver("build_type")
    if build not in reuse.factor_by_build_type:
        return set(), ONE
    tasks: list[TaskType] = t.param("reuse", "tasks")
    factor: Decimal = t.param("reuse", "factor_by_build_type", build)
    names = ", ".join(task.value for task in tasks)
    return set(tasks), t.step("M_reuse", f"{build} build, on {names}", factor)


def base_effort(ctx: PricingContext, ci: ComponentInstanceIn) -> ComponentEffort:
    """Effort in person-days before compression (used to size the timeline).

    effort = Σ_task base_pd[size] × quantity × share × M_complexity × M_nfr × licence_factor
             × M_reuse(task) × (1 − min(max_saving, saving_task × maturity_scale))
    """
    catalog = ctx.inp.catalog.get(ci.catalog_key)
    scratch = ctx.builder(
        line_key="scratch",
        stage="build",
        bucket=catalog.bucket,
        year=0,
        label="",
        formula_id="component_labour.v2",
    )
    per_task, saved = _task_efforts(scratch, ci, catalog)
    return ComponentEffort(ci, catalog, dsum(per_task.values()), dsum(saved.values()))


def _task_efforts(
    t: LineBuilder, ci: ComponentInstanceIn, catalog: CatalogComponent
) -> tuple[dict[TaskType, Decimal], dict[TaskType, Decimal]]:
    """(effort, effort saved by AI tools) per task type, in person-days. The saving is zero when
    `ai_saving_applies` says the component's effort data must not be discounted."""
    base: Decimal = catalog.base_effort_pd[Size(ci.size)] * t.calibration("effort_multiplier")
    m_cx: Decimal = t.param("complexity_multipliers", ci.complexity.value)
    m_nfr = nfr_multiplier(t, catalog)
    lic = ONE
    if _uses_licence(t.ctx, catalog) and catalog.licence is not None:
        t.driver("licensing")
        lic = catalog.licence.effort_factor
    applies = ai_saving_applies(t.ctx, catalog)
    unknown = applies and catalog.source_era is BaselineEra.UNKNOWN
    if unknown and t.ctx.p.ai_productivity.unknown_era_is_pre_ai:
        t.param("ai_productivity", "unknown_era_is_pre_ai")
    if applies:
        maturity = t.driver("team_ai_maturity")
        scale: Decimal = t.param("ai_productivity", "maturity_scale", maturity)
        cap: Decimal = t.param("ai_productivity", "max_saving")
    reused, m_reuse = reuse_multiplier(t, ci)
    efforts: dict[TaskType, Decimal] = {}
    saved: dict[TaskType, Decimal] = {}
    for task, share in catalog.task_mix.items():
        without_ai = base * ci.quantity * share * m_cx * m_nfr * lic
        if task in reused:
            without_ai *= m_reuse
        effective_saving = ZERO
        if applies:
            saving: Decimal = t.param("ai_productivity", "task_savings", task.value)
            effective_saving = min(cap, saving * scale)
        efforts[task] = without_ai * (ONE - effective_saving)
        saved[task] = without_ai * effective_saving
    return efforts, saved


def component_line(
    ctx: PricingContext, effort: ComponentEffort, compression: Decimal
) -> CostLineOut:
    """Price one component instance; the line carries per-task steps and role person-days.
    Catalog v6+ components also record where their effort data comes from and whether the AI
    saving was applied (formula component_labour.v3); with a parameter set that prices reuse
    (v19+), the formula is component_labour.v4."""
    ci, catalog = effort.instance, effort.catalog
    stage = catalog.bucket.split(".", 1)[0]
    if catalog.source_era is None:
        formula_id = "component_labour.v2"
    else:
        formula_id = "component_labour.v3" if ctx.p.reuse is None else "component_labour.v4"
    t = ctx.builder(
        line_key=f"{catalog.bucket}/{ci.id}",
        stage=stage,
        bucket=catalog.bucket,
        year=0,
        label=ci.label or catalog.name,
        formula_id=formula_id,
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
    if catalog.source_era is not None:
        t.add_input(
            source_era=catalog.source_era.value,
            evidence=[e.id for e in catalog.evidence],
            ai_saving="applied" if ai_saving_applies(ctx, catalog) else "not applied",
            era_scenario=ctx.inp.era_scenario,
        )
    efforts, _ = _task_efforts(t, ci, catalog)
    total = ZERO
    for task, pd in efforts.items():
        for role_key, share in task_role_shares(t, task):
            rate = t.rate_local(role_key)
            pd_c = pd * share * compression
            of = "" if share == ONE else f" × share {share}"
            cost = t.step(
                f"{task.value} → {role_key}",
                f"{pd:.4f} pd{of} × compression {compression:.4f} × ₹{rate}/pd",
                pd_c * rate,
            )
            t.add_role_pd(role_key, pd_c)
            total += cost
    t.add_input(effort_pd=str(dsum(efforts.values()) * compression))
    spreads.clarity(t, ctx.component_clarity(ci))
    spreads.template_match(t)
    spreads.tags(t, list(catalog.tags))
    spreads.compression(t, compression)
    if ci.hard_problem:
        spreads.hard_problem(t)
    return t.finish(total)


def task_role_shares(t: LineBuilder, task: TaskType) -> list[tuple[str, Decimal]]:
    """Who does a task: [(role, share)]. task_roles.split (v19+) shares a task between roles,
    e.g. review = 0.7 developer (peer review) + 0.3 senior developer (sign-off); otherwise the
    task's one role does all of it."""
    if task in t.ctx.p.task_roles.split:
        shares: dict[str, Decimal] = t.param("task_roles", "split", task.value)
        return list(shares.items())
    role_key: str = t.param("task_roles", "roles", task.value)
    return [(role_key, ONE)]


AI_REVIEW_KEY = "build.testing/ai_code_review"


def ai_review_line(
    ctx: PricingContext, efforts: list[ComponentEffort], compression: Decimal
) -> list[CostLineOut]:
    """Extra review and security checks of AI-written code (parameter sets v12+): AI tools save
    effort, but their output must be read, tested and fixed by people.

      review_pd = review_share_of_saved × Σ_component ai_saved_pd × M_compression
      cost      = review_pd × rate(review_role)
    """
    ai = ctx.p.ai_productivity
    saved = dsum(e.ai_saved_pd for e in efforts)
    if ai.review_share_of_saved is None or ai.review_role is None or saved == ZERO:
        return []
    t = ctx.builder(
        line_key=AI_REVIEW_KEY,
        stage="build",
        bucket="build.testing",
        year=0,
        label="Extra review and security checks of AI-written code",
        formula_id="build.ai_code_review.v1",
    )
    t.driver("team_ai_maturity")
    share: Decimal = t.param("ai_productivity", "review_share_of_saved")
    role: str = t.param("ai_productivity", "review_role")
    rate = t.rate_local(role)
    pd = t.step(
        "review person-days",
        f"{share} × {saved:.4f} AI-saved person-days × compression {compression:.4f}",
        share * saved * compression,
    )
    t.add_role_pd(role, pd)
    t.add_input(ai_saved_pd=str(saved))
    spreads.clarity(t, ctx.overall_clarity())
    return [t.finish(t.step("cost", f"{pd:.4f} pd × ₹{rate}/pd", pd * rate))]

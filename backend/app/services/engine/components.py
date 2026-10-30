"""Component labour cost (brief 7.1)."""

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal

from app.services.engine import spreads
from app.services.engine.context import LineBuilder, PricingContext
from app.services.engine.inputs import ComponentInstanceIn
from app.services.engine.money import ONE, ZERO, dsum, paise_to_rupees, to_paise
from app.services.engine.outputs import CostLineOut
from app.services.engine.reference import (
    BaselineEra,
    CatalogComponent,
    Complexity,
    Driver,
    EffortCaps,
    Size,
    TaskType,
)


@dataclass(frozen=True)
class ComponentEffort:
    instance: ComponentInstanceIn
    catalog: CatalogComponent
    effort_pd: Decimal  # before schedule compression
    ai_saved_pd: Decimal = ZERO  # effort the team's AI tools save (before compression)


@dataclass(frozen=True)
class EffortPlan:
    """What every component's effort depends on beyond itself (parameter sets v20+), worked out
    once from all components: the project's reuse ratio for whole-system testing, and the
    scale each effort cap puts on its tasks (1 = not capped). Totals are kept for the trace."""

    project_reuse_ratio: Decimal = ONE
    review_scale: Decimal = ONE
    pre_build_scale: Decimal = ONE
    architecture_scale: Decimal = ONE
    tests_scale: Decimal = ONE
    base_pd: Decimal = ZERO
    review_pd: Decimal = ZERO
    pre_build_pd: Decimal = ZERO
    architecture_pd: Decimal = ZERO
    architecture_cap_pd: Decimal = ZERO
    tests_pd: Decimal = ZERO
    tested_pd: Decimal = ZERO

    def scale(self, caps: EffortCaps | None, stage: str, task: TaskType) -> Decimal:
        if caps is None:
            return ONE
        s = self.pre_build_scale if stage == PRE_BUILD else ONE
        if task is caps.review_task:
            s *= self.review_scale
        if task is caps.architecture_task:
            s *= self.architecture_scale
        if task is caps.tests_task:
            s *= self.tests_scale
        return s


NO_PLAN = EffortPlan()
PRE_BUILD = "pre_build"
BUILD = "build"


def _stage(catalog: CatalogComponent) -> str:
    return catalog.bucket.split(".", 1)[0]


def _scratch(ctx: PricingContext, catalog: CatalogComponent) -> LineBuilder:
    """A builder whose trace is thrown away (effort before pricing)."""
    return ctx.builder(
        line_key="scratch",
        stage="build",
        bucket=catalog.bucket,
        year=0,
        label="",
        formula_id="component_labour.v2",
    )


def effort_plan(ctx: PricingContext) -> EffortPlan:
    if ctx.effort_plan is None:
        ctx.effort_plan = _make_plan(ctx)
    return ctx.effort_plan


def _make_plan(ctx: PricingContext) -> EffortPlan:
    """1. project_reuse_ratio = Σ work after reuse / Σ work before, over build-stage components
          (work = every task but reuse.follow_tasks; project-wide testing blocks left out).
    2. Each component's effort with that ratio, uncapped (after AI savings).
    3. The caps (EffortCaps), in order: review, pre-build (after the review cap), architect
       (after both), tests (v28+, by project size; on the work before AI savings, so the
       team's AI tools still save on the capped tests). Each scale = min(1, ceiling / total);
       no build base = no caps."""
    reuse, caps = ctx.p.reuse, ctx.p.effort_caps
    if (reuse is None or not reuse.follow_tasks) and caps is None:
        return NO_PLAN
    items = [(ci, ctx.inp.catalog.get(ci.catalog_key)) for ci in ctx.inp.components]
    ratio = ONE
    if reuse is not None and reuse.follow_tasks:
        before = after = ZERO
        for ci, catalog in items:
            if _stage(catalog) != BUILD or catalog.key in reuse.project_wide_components:
                continue
            b, a = _work(_scratch(ctx, catalog), ci, catalog)
            before, after = before + b, after + a
        ratio = after / before if before else ONE
    plan = EffortPlan(project_reuse_ratio=ratio)
    if caps is None:
        return plan
    worked = [
        (ci, catalog, *_task_efforts(_scratch(ctx, catalog), ci, catalog, plan))
        for ci, catalog in items
    ]
    efforts = [(ci, catalog, e) for ci, catalog, e, _ in worked]
    base = dsum(
        pd
        for _, catalog, e in efforts
        if _stage(catalog) == BUILD
        for task, pd in e.items()
        if task in caps.base_tasks
    )
    if base == ZERO:
        return plan
    review = dsum(e.get(caps.review_task, ZERO) for _, _, e in efforts)
    review_share, pre_share = cap_shares(ctx, caps)
    review_scale = min(ONE, review_share * base / review) if review else ONE
    multipliers = ctx.p.complexity_multipliers
    by_usual = caps.pre_build_cap_at_usual_complexity

    def at_usual(ci: ComponentInstanceIn) -> Decimal:
        """v29+: the pre-build cap counts each block at the usual (medium) complexity."""
        return multipliers[Complexity.MEDIUM] / multipliers[ci.complexity] if by_usual else ONE

    pre = dsum(
        pd * (review_scale if task is caps.review_task else ONE) * at_usual(ci)
        for ci, catalog, e in efforts
        if _stage(catalog) == PRE_BUILD
        for task, pd in e.items()
    )
    pre_scale = min(ONE, pre_share * base / pre) if pre else ONE
    arch = dsum(
        e.get(caps.architecture_task, ZERO) * (pre_scale if _stage(catalog) == PRE_BUILD else ONE)
        for _, catalog, e in efforts
    )
    hard = sum(1 for ci, _, _ in efforts if ci.hard_problem)
    arch_cap = architecture_floor(ctx, caps, base) + caps.architecture_pd_per_hard_problem * hard
    tests = tested = ZERO
    tests_scale = ONE
    near, edge = size_edge(ctx)
    tests_share = caps.tests_max_share_by_size.get(ctx.q.project_size or "")
    near_tests = caps.tests_max_share_by_size.get(near or "")
    if caps.tests_task is not None and (tests_share is not None or near_tests is not None):
        # before AI savings: the cap sets the work, the team's AI tools then save on it
        unsaved = [
            (catalog, {k: pd + saved.get(k, ZERO) for k, pd in e.items()})
            for _, catalog, e, saved in worked
        ]
        tests = dsum(e.get(caps.tests_task, ZERO) for _, e in unsaved)
        tested = dsum(  # the development work tested: the build base without the tests
            pd
            for catalog, e in unsaved
            if _stage(catalog) == BUILD
            for task, pd in e.items()
            if task in caps.base_tasks and task is not caps.tests_task
        )
        tests_scale = between(
            tests_scale_at(tests_share, tested, tests),
            tests_scale_at(near_tests, tested, tests),
            edge,
        )
    return EffortPlan(
        project_reuse_ratio=ratio,
        review_scale=review_scale,
        pre_build_scale=pre_scale,
        architecture_scale=min(ONE, arch_cap / arch) if arch else ONE,
        tests_scale=tests_scale,
        base_pd=base,
        review_pd=review,
        pre_build_pd=pre,
        architecture_pd=arch,
        architecture_cap_pd=arch_cap,
        tests_pd=tests,
        tested_pd=tested,
    )


def size_edge(ctx: PricingContext) -> tuple[str | None, Decimal]:
    """(neighbouring size, its share) near the edge of two project sizes when the parameter
    set blends there (v30+, OPEN_QUESTIONS 187); (None, 0) otherwise."""
    caps, blend = ctx.p.effort_caps, ctx.q.size_blend
    if caps is None or not caps.blend_across_size_edge or blend is None:
        return None, ZERO
    return blend.size, blend.share


def between(own: Decimal, near: Decimal, share: Decimal) -> Decimal:
    """(1 − share) × own + share × near: own when share is 0."""
    return own if share == ZERO else (ONE - share) * own + share * near


def tests_scale_at(share: Decimal | None, tested: Decimal, tests: Decimal) -> Decimal:
    """min(1, share × tested / tests): 1 when the size has no tests cap or there are no tests."""
    return min(ONE, share * tested / tests) if share is not None and tests else ONE


def cap_shares(ctx: PricingContext, caps: EffortCaps) -> tuple[Decimal, Decimal]:
    """(review, pre-build) cap shares: by project size when listed, else the flat shares; near
    a size edge (v30+) between the two sizes' shares."""
    size = ctx.q.project_size or ""
    near, edge = size_edge(ctx)
    review = caps.review_max_share_by_size
    pre = caps.pre_build_max_share_by_size
    return (
        between(
            review.get(size, caps.review_max_share),
            review.get(near or "", caps.review_max_share),
            edge,
        ),
        between(
            pre.get(size, caps.pre_build_max_share),
            pre.get(near or "", caps.pre_build_max_share),
            edge,
        ),
    )


def architecture_floor(ctx: PricingContext, caps: EffortCaps, base: Decimal) -> Decimal:
    """The architect's days before hard problems: max(architecture_base_pd, share[size] × build
    base) when the project size is listed in architecture_max_share_by_size, else the base;
    near a size edge (v30+) between the two sizes' floors."""

    def floor(size: str | None) -> Decimal:
        share = caps.architecture_max_share_by_size.get(size or "")
        if share is None:
            return caps.architecture_base_pd
        return max(caps.architecture_base_pd, share * base)

    near, edge = size_edge(ctx)
    return between(floor(ctx.q.project_size), floor(near), edge)


def _cap_share(t: LineBuilder, caps: EffortCaps, which: str) -> Decimal:
    """Record the cap share used (by project size when listed) on the line's trace; near a
    size edge (v30+) the share between the two sizes."""
    near, edge = size_edge(t.ctx)
    if near is not None:
        t.driver("project_size")
        t.driver("size_blend")
        table: dict[str, Decimal] = getattr(caps, f"{which}_by_size")
        shares: list[Decimal] = [
            t.param("effort_caps", f"{which}_by_size", s)
            if s in table
            else t.param("effort_caps", which)
            for s in (t.ctx.q.project_size or "", near)
        ]
        value: Decimal = t.step(
            f"{which} between sizes",
            f"(1 − {edge}) × {shares[0]} + {edge} × {shares[1]} ({near})",
            between(shares[0], shares[1], edge),
        )
        return value
    size = t.ctx.q.project_size
    if size is not None and size in getattr(caps, f"{which}_by_size"):
        t.driver("project_size")
        share: Decimal = t.param("effort_caps", f"{which}_by_size", size)
        return share
    flat: Decimal = t.param("effort_caps", which)
    return flat


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
             × M_reuse(task) × M_follow(task) × cap(task)
             × (1 − min(max_saving, saving_task × maturity_scale))
    """
    catalog = ctx.inp.catalog.get(ci.catalog_key)
    per_task, saved = _task_efforts(_scratch(ctx, catalog), ci, catalog)
    return ComponentEffort(ci, catalog, dsum(per_task.values()), dsum(saved.values()))


def mixed_base_pd(ci: ComponentInstanceIn, catalog: CatalogComponent) -> Decimal:
    """base_effort_pd[size], or Σ base_effort_pd[s] × share for a block priced between sizes
    (size_mix, OPEN_QUESTIONS 183)."""
    if ci.size_mix is None:
        return catalog.base_effort_pd[Size(ci.size)]
    return dsum(catalog.base_effort_pd[s] * share for s, share in ci.size_mix.items())


def _raw_efforts(
    t: LineBuilder, ci: ComponentInstanceIn, catalog: CatalogComponent
) -> dict[TaskType, Decimal]:
    """Per task, before reuse, caps and AI savings:
    base_pd[size] × effort_multiplier × quantity × share × M_complexity × M_nfr × licence."""
    base = mixed_base_pd(ci, catalog) * t.calibration("effort_multiplier")
    m_cx: Decimal = t.param("complexity_multipliers", ci.complexity.value)
    m_nfr = nfr_multiplier(t, catalog)
    lic = ONE
    if _uses_licence(t.ctx, catalog) and catalog.licence is not None:
        t.driver("licensing")
        lic = catalog.licence.effort_factor
    return {
        task: base * ci.quantity * share * m_cx * m_nfr * lic
        for task, share in catalog.task_mix.items()
    }


def _work(
    t: LineBuilder, ci: ComponentInstanceIn, catalog: CatalogComponent
) -> tuple[Decimal, Decimal]:
    """(before, after) reuse of a component's work: every task except reuse.follow_tasks."""
    raw = _raw_efforts(t, ci, catalog)
    reused, m_reuse = reuse_multiplier(t, ci)
    follow = set(t.ctx.p.reuse.follow_tasks) if t.ctx.p.reuse else set()
    work = {task: pd for task, pd in raw.items() if task not in follow}
    after = dsum(pd * (m_reuse if task in reused else ONE) for task, pd in work.items())
    return dsum(work.values()), after


def follow_multiplier(
    t: LineBuilder,
    catalog: CatalogComponent,
    raw: dict[TaskType, Decimal],
    reused: set[TaskType],
    m_reuse: Decimal,
    plan: EffortPlan,
) -> tuple[set[TaskType], Decimal]:
    """(follow tasks, M_follow) (parameter sets v20+): review and tests shrink with the work
    they check.

      M_follow = Σ own work after reuse / Σ own work before   (work = the non-follow tasks)
      M_follow = project_reuse_ratio                           (reuse.project_wide_components)

    1 when nothing in the component is reused."""
    reuse = t.ctx.p.reuse
    if reuse is None or not reuse.follow_tasks:
        return set(), ONE
    follow = set(t.param("reuse", "follow_tasks")) & set(raw)
    if not follow:
        return set(), ONE
    if catalog.key in reuse.project_wide_components:
        t.param("reuse", "project_wide_components")
        ratio = plan.project_reuse_ratio
        if ratio == ONE:
            return set(), ONE
        expr = "project build work after reuse / before"
        return follow, t.step("M_follow", f"{expr} = {ratio:.4f}", ratio)
    work = {task: pd for task, pd in raw.items() if task not in follow}
    before = dsum(work.values())
    after = dsum(pd * (m_reuse if task in reused else ONE) for task, pd in work.items())
    if before == ZERO or after == before:
        return set(), ONE
    expr = f"own work after reuse {after:.4f} / before {before:.4f}"
    return follow, t.step("M_follow", expr, after / before)


def _caps(
    t: LineBuilder, catalog: CatalogComponent, tasks: set[TaskType], plan: EffortPlan
) -> None:
    """Record the effort caps that touch this component (parameter sets v20+)."""
    caps = t.ctx.p.effort_caps
    if caps is None:
        return
    stage = _stage(catalog)
    if caps.review_task in tasks and plan.review_scale < ONE:
        share = _cap_share(t, caps, "review_max_share")
        t.step(
            f"cap {caps.review_task.value}",
            f"min(1, {share} × build {plan.base_pd:.2f} pd / review {plan.review_pd:.2f} pd)",
            plan.review_scale,
        )
    if stage == PRE_BUILD and plan.pre_build_scale < ONE:
        pre = _cap_share(t, caps, "pre_build_max_share")
        t.step(
            "cap pre-build",
            f"min(1, {pre} × build {plan.base_pd:.2f} pd / pre-build {plan.pre_build_pd:.2f} pd)",
            plan.pre_build_scale,
        )
    if caps.architecture_task in tasks and plan.architecture_scale < ONE:
        t.param("effort_caps", "architecture_base_pd")
        t.param("effort_caps", "architecture_pd_per_hard_problem")
        size = t.ctx.q.project_size
        near, edge = size_edge(t.ctx)
        if near is not None:
            t.driver("project_size")
            t.driver("size_blend")
            t.param("effort_caps", "architecture_max_share_by_size")
            between_floor: Decimal = t.step(
                "architect floor between sizes",
                f"(1 − {edge}) × floor[{size}] + {edge} × floor[{near}], floor = max("
                f"{caps.architecture_base_pd}, share × build {plan.base_pd:.2f} pd)",
                architecture_floor(t.ctx, caps, plan.base_pd),
            )
            floor = f"{between_floor:.2f}"
        elif size is not None and size in caps.architecture_max_share_by_size:
            t.driver("project_size")
            share = t.param("effort_caps", "architecture_max_share_by_size", size)
            floor = f"max({caps.architecture_base_pd}, {share} × build {plan.base_pd:.2f} pd)"
        else:
            floor = f"{caps.architecture_base_pd}"
        t.step(
            f"cap {caps.architecture_task.value}",
            f"min(1, ({floor} + {caps.architecture_pd_per_hard_problem}"
            f" × hard problems) {plan.architecture_cap_pd:.2f} pd"
            f" / {plan.architecture_pd:.2f} pd)",
            plan.architecture_scale,
        )
    if caps.tests_task in tasks and plan.tests_scale < ONE:
        sized: str = t.driver("project_size")
        near, edge = size_edge(t.ctx)
        if near is not None:
            t.driver("size_blend")
            t.param("effort_caps", "tests_max_share_by_size")
            t.param("effort_caps", "tests_task")
            t.step(
                f"cap {caps.tests_task.value} between sizes",
                f"(1 − {edge}) × scale[{sized}] + {edge} × scale[{near}], scale = min(1,"
                f" share × tested work {plan.tested_pd:.2f} pd / tests {plan.tests_pd:.2f} pd)"
                " (1 without a cap)",
                plan.tests_scale,
            )
        else:
            share = t.param("effort_caps", "tests_max_share_by_size", sized)
            t.param("effort_caps", "tests_task")
            t.step(
                f"cap {caps.tests_task.value}",
                f"min(1, {share} × tested work {plan.tested_pd:.2f} pd"
                f" / tests {plan.tests_pd:.2f} pd)",
                plan.tests_scale,
            )


def _task_efforts(
    t: LineBuilder,
    ci: ComponentInstanceIn,
    catalog: CatalogComponent,
    plan: EffortPlan | None = None,
) -> tuple[dict[TaskType, Decimal], dict[TaskType, Decimal]]:
    """(effort, effort saved by AI tools) per task type, in person-days. The saving is zero when
    `ai_saving_applies` says the component's effort data must not be discounted. `plan` (the
    caps and project reuse ratio) defaults to the project's; `_make_plan` passes its own."""
    plan = plan or effort_plan(t.ctx)
    raw = _raw_efforts(t, ci, catalog)
    applies = ai_saving_applies(t.ctx, catalog)
    unknown = applies and catalog.source_era is BaselineEra.UNKNOWN
    if unknown and t.ctx.p.ai_productivity.unknown_era_is_pre_ai:
        t.param("ai_productivity", "unknown_era_is_pre_ai")
    if applies:
        maturity = t.driver("team_ai_maturity")
        scale: Decimal = t.param("ai_productivity", "maturity_scale", maturity)
        cap: Decimal = t.param("ai_productivity", "max_saving")
    reused, m_reuse = reuse_multiplier(t, ci)
    follow, m_follow = follow_multiplier(t, catalog, raw, reused, m_reuse, plan)
    caps, stage = t.ctx.p.effort_caps, _stage(catalog)
    if plan is not NO_PLAN:
        _caps(t, catalog, set(raw), plan)
    efforts: dict[TaskType, Decimal] = {}
    saved: dict[TaskType, Decimal] = {}
    for task, without_ai in raw.items():
        if task in reused:
            without_ai *= m_reuse
        elif task in follow:
            without_ai *= m_follow
        without_ai *= plan.scale(caps, stage, task)
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
    (v19+), the formula is component_labour.v4; with review and tests following the reuse or
    effort caps (v20+), component_labour.v5; v29+ (pre-build cap at the usual complexity)
    or a block priced between sizes, v6."""
    ci, catalog = effort.instance, effort.catalog
    stage = _stage(catalog)
    caps = ctx.p.effort_caps
    if size_edge(ctx)[0] is not None:
        formula_id = "component_labour.v7"
    elif ci.size_mix is not None or (caps is not None and caps.pre_build_cap_at_usual_complexity):
        formula_id = "component_labour.v6"
    elif effort_plan(ctx) is not NO_PLAN:
        formula_id = "component_labour.v5"
    elif catalog.source_era is None:
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
        base_effort_pd=str(mixed_base_pd(ci, catalog)),
        **({"size_mix": {s.value: str(v) for s, v in ci.size_mix.items()}} if ci.size_mix else {}),
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
      cost      = review_pd × rate(review_role)                          (v1)
      cost      = Σ_role review_pd × share_role × rate(role)             (v2: review_task's roles,
                                                                          e.g. 0.7 developer /
                                                                          0.3 senior developer)
    The saved effort is after reuse and the effort caps, so only work still priced is reviewed.
    """
    ai = ctx.p.ai_productivity
    saved = dsum(e.ai_saved_pd for e in efforts)
    if ai.review_share_of_saved is None or saved == ZERO:
        return []
    if ai.review_task is None and ai.review_role is None:
        return []
    t = ctx.builder(
        line_key=AI_REVIEW_KEY,
        stage="build",
        bucket="build.testing",
        year=0,
        label="Extra review and security checks of AI-written code",
        formula_id="build.ai_code_review.v1"
        if ai.review_task is None
        else "build.ai_code_review.v2",
    )
    t.follows_build = True  # a share of the effort the AI tools save
    t.driver("team_ai_maturity")
    share: Decimal = t.param("ai_productivity", "review_share_of_saved")
    if ai.review_task is None:  # v1: one role, traced in the order first recorded
        role: str = t.param("ai_productivity", "review_role")
        rate = t.rate_local(role)
    pd = t.step(
        "review person-days",
        f"{share} × {saved:.4f} AI-saved person-days × compression {compression:.4f}",
        share * saved * compression,
    )
    if ai.review_task is None:
        t.add_role_pd(role, pd)
        total = t.step("cost", f"{pd:.4f} pd × ₹{rate}/pd", pd * rate)
    else:
        t.param("ai_productivity", "review_task")
        total = ZERO
        for role, role_share in task_role_shares(t, ai.review_task):
            rate = t.rate_local(role)
            role_pd = pd * role_share
            t.add_role_pd(role, role_pd)
            total += t.step(
                f"cost → {role}", f"{pd:.4f} pd × share {role_share} × ₹{rate}/pd", role_pd * rate
            )
    t.add_input(ai_saved_pd=str(saved))
    spreads.clarity(t, ctx.overall_clarity())
    return [t.finish(total)]


AI_KEPT_KEY = "commercial.margin/ai_saving_kept"
AI_CODING_TOOLS_KEY = "build.tools/ai_coding"
SHARE_QUANTUM = Decimal("0.0001")


def ai_saving_kept(
    ctx: PricingContext,
    efforts: list[ComponentEffort],
    compression: Decimal,
    base: Sequence[CostLineOut],
) -> tuple[LineBuilder, Decimal] | None:
    """The AI saving the estimate identifies, and the part kept as margin (the answer
    ai_passthrough_percent, asked on every estimate; formula commercial.ai_saving_kept.v1):

      saved      = Σ_component Σ_task ai_saved_pd × share_role × compression × rate(role)
      identified = max(0, saved − AI review line − AI coding tools line)
      kept       = identified × (1 − ai_passthrough_percent)

    The cost lines are the same whatever the answer. None when it is not answered (all of the
    saving passed through, as before the answer existed)."""
    if ctx.q.ai_passthrough_percent is None:
        return None
    t = ctx.builder(
        line_key=AI_KEPT_KEY,
        stage="commercial",
        bucket="commercial.margin",
        year=0,
        label="AI saving kept (margin)",
        formula_id="commercial.ai_saving_kept.v1",
    )
    passthrough: Decimal = t.driver("ai_passthrough_percent")
    saved = without = ZERO
    for e in efforts:
        per_task, saved_task = _task_efforts(_scratch(ctx, e.catalog), e.instance, e.catalog)
        for task, pd in per_task.items():
            for role, share in task_role_shares(t, task):
                rate = t.rate_local(role)
                without += (pd + saved_task[task]) * share * compression * rate
                saved += saved_task[task] * share * compression * rate
    saved = t.step(
        "AI-saved labour", "Σ AI-saved person-days × role share × compression × rate", saved
    )
    review = paise_to_rupees(sum(ln.likely_paise for ln in base if ln.line_key == AI_REVIEW_KEY))
    tools = paise_to_rupees(
        sum(ln.likely_paise for ln in base if ln.line_key == AI_CODING_TOOLS_KEY)
    )
    identified = t.step(
        "AI saving identified",
        f"max(0, ₹{saved:.2f} − AI review ₹{review} − AI coding tools ₹{tools})",
        max(ZERO, saved - review - tools),
    )
    t.add_input(
        ai_saving_identified_paise=to_paise(identified),
        build_labour_without_ai_paise=to_paise(without),
        ai_saving_share=str((identified / without if without else ZERO).quantize(SHARE_QUANTUM)),
        ai_passthrough_percent=str(passthrough),
    )
    kept = t.step(
        "kept as margin",
        f"₹{identified:.2f} × (1 − passed to the client {passthrough})",
        identified * (ONE - passthrough),
    )
    return t, kept

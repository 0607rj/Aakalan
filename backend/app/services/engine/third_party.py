"""Third-party costs (parameter sets with a `third_party` group): build-phase tool seats,
usage-billed services (SMS, email, maps, eKYC, app stores, web firewall), AI features other
than the chatbot, content translation, and the costs the client pays directly (not quoted).
Older parameter sets have no `third_party` group, so none of these lines appear for them."""

from decimal import Decimal

from app.services.engine import spreads
from app.services.engine.context import LineBuilder, PricingContext
from app.services.engine.money import ONE, ZERO
from app.services.engine.outputs import ClientPaidNoteOut, CostLineOut, TraceRate
from app.services.engine.reference import PLACEHOLDER, ThirdParty, UsageService
from app.services.engine.run_costs import ai_runtime_lines
from app.services.hosting.sizing import hosting_lines

THIRD_PARTY_BUCKET = "run.third_party_services"
BUILD_STAGES = ("pre_build", "build")
NO_AI = "none"


def _in_scope(ctx: PricingContext) -> set[str]:
    return {c.catalog_key for c in ctx.inp.components}


def _link(t: LineBuilder, keys: list[str]) -> None:
    """Cite the requirements behind the components that trigger this line."""
    for c in t.ctx.inp.components:
        if c.catalog_key in keys:
            for rid in c.requirement_ids:
                if rid not in t.requirement_ids:
                    t.requirement_ids.append(rid)


# --- build-phase tools -------------------------------------------------------------------------


def dev_tools_lines(ctx: PricingContext, base: list[CostLineOut]) -> list[CostLineOut]:
    """seats = Σ build person-days / pd_per_month (one seat per person-month of build);
    cost = seats × seat_month_rate, for the AI coding assistant (when the team uses AI tools)
    and the core dev tools suite (code hosting, issue tracker, design tool)."""
    tp = ctx.p.third_party
    if tp is None or tp.dev_tools is None:
        return []
    pd = sum((pd for ln in base if ln.stage in BUILD_STAGES for pd in ln.role_pd.values()), ZERO)
    if pd == ZERO:
        return []
    lines = []
    for item, label, rate_field in (
        ("ai_coding", "AI coding assistant subscriptions", "ai_coding_rate_key"),
        ("dev_suite", "Developer tools (code hosting, tracker, design)", "dev_suite_rate_key"),
    ):
        t = ctx.builder(
            line_key=f"build.tools/{item}",
            stage="build",
            bucket="build.tools",
            year=0,
            label=label,
            formula_id="build.dev_tools.v1",
        )
        if item == "ai_coding" and t.driver("team_ai_maturity") == NO_AI:
            continue
        per_month: Decimal = t.param("calendar", "pd_per_month")
        seats = t.step("seat-months", f"{pd:.2f} build person-days / {per_month}", pd / per_month)
        rate = t.rate_local(t.param("third_party", "dev_tools", rate_field))
        spreads.clarity(t, ctx.overall_clarity())
        lines.append(t.finish(seats * rate))
    return lines


# --- usage-billed services ---------------------------------------------------------------------


def _applies(ctx: PricingContext, s: UsageService) -> bool:
    if s.components and not set(s.components) & _in_scope(ctx):
        return False
    if s.segments and ctx.q.buyer_segment not in s.segments:
        return False
    if s.regions and ctx.inp.rate_card.region not in s.regions:
        return False
    return ctx.q.users_total >= s.min_users


def _service_line(ctx: PricingContext, s: UsageService, year: int) -> CostLineOut | None:
    if s.basis == "fixed" and s.rate_period == "one_off" and year != 1:
        return None
    t = ctx.builder(
        line_key=f"{THIRD_PARTY_BUCKET}/{s.key}/y{year}",
        stage="run",
        bucket=THIRD_PARTY_BUCKET,
        year=year,
        label=f"{s.label} (year {year})",
        formula_id=f"third_party.{s.basis}.v1",
    )
    t.driver("om_years")
    _link(t, s.components)
    services = ctx.p.third_party.services if ctx.p.third_party else []
    path = ("third_party", "services", next(i for i, x in enumerate(services) if x.key == s.key))
    months = ctx.months_per_year()
    if s.basis == "monthly":
        users: int = t.driver("users_total")
        active: Decimal = t.param("hosting", "monthly_active_share")
        per_user: Decimal = t.param(*path, "units_per_active_user_month")
        free: Decimal = t.param(*path, "free_units_per_month")
        units = t.step(
            "billable units per year",
            f"max(0, {users} × {active} × {per_user} − {free}) × {months}",
            max(ZERO, users * active * per_user - free) * months,
        )
        spreads.fixed(t, "hosting")
    elif s.basis == "per_user":
        users = t.driver("users_total")
        field = "first_year_units_per_user" if year == 1 else "later_year_units_per_user"
        per_user = t.param(*path, field)
        units = t.step("units in the year", f"{users} × {per_user}", users * per_user)
        spreads.fixed(t, "hosting")
    else:
        count: Decimal = t.param(*path, "count")
        periods = months if s.rate_period == "month" else ONE
        units = t.step("units in the year", f"{count} × {periods}", count * periods)
        spreads.fixed(t, "fixed_fee")
    if units == ZERO:
        return None
    rate = t.rate_local(t.param(*path, "rate_key"))
    per_units: Decimal = t.param(*path, "per_units")
    esc = t.escalation("prices", year)
    spreads.om_year(t, year)
    return t.finish(units * rate / per_units * esc)


def _services_lines(ctx: PricingContext, services: list[UsageService]) -> list[CostLineOut]:
    lines = []
    for s in services:
        if not _applies(ctx, s):
            continue
        for year in range(1, ctx.q.om_years + 1):
            line = _service_line(ctx, s, year)
            if line is not None:
                lines.append(line)
    return lines


def ai_feature_lines(ctx: PricingContext) -> list[CostLineOut]:
    """instances × users × active_share × calls_per_active_user_month × months_per_year
    × (tokens_in × price_in + tokens_out × price_out) / tokens_per_unit
    × (1 + annual_price_change)^year — API mode only (self-hosted GPUs are sized separately)."""
    tp = ctx.p.third_party
    if tp is None or tp.ai_features is None or ctx.q.ai_runtime_mode != "api":
        return []
    instances = sum(
        c.quantity for c in ctx.inp.components if c.catalog_key in tp.ai_features.components
    )
    if not instances or ctx.q.users_total == 0:
        return []
    lines = []
    for year in range(1, ctx.q.om_years + 1):
        t = ctx.builder(
            line_key=f"run.ai_runtime/ai_features/y{year}",
            stage="run",
            bucket="run.ai_runtime",
            year=year,
            label=f"AI features usage (year {year})",
            formula_id="ai_runtime.features.v1",
        )
        t.driver("om_years")
        t.driver("ai_runtime_mode")
        _link(t, tp.ai_features.components)
        users: int = t.driver("users_total")
        active: Decimal = t.param("hosting", "monthly_active_share")
        calls: Decimal = t.param("third_party", "ai_features", "calls_per_active_user_month")
        tin: Decimal = t.param("third_party", "ai_features", "tokens_in_per_call")
        tout: Decimal = t.param("third_party", "ai_features", "tokens_out_per_call")
        per_unit: Decimal = t.param("ai_runtime", "tokens_per_unit")
        change: Decimal = t.param("ai_runtime", "annual_price_change")
        p_in, p_out = t.token_rates()
        months = ctx.months_per_year()
        n_calls = t.step(
            "AI calls per year",
            f"{instances} × {users} × {active} × {calls} × {months}",
            instances * users * active * calls * months,
        )
        per_call = t.step(
            "cost per call",
            f"({tin} × {p_in:.4f} + {tout} × {p_out:.4f}) / {per_unit}",
            (tin * p_in + tout * p_out) / per_unit,
        )
        spreads.fixed(t, "ai_runtime")
        spreads.om_year(t, year)
        lines.append(t.finish(n_calls * per_call * (ONE + change) ** year))
    return lines


# --- content translation -----------------------------------------------------------------------


def translation_lines(ctx: PricingContext) -> list[CostLineOut]:
    """words = words_per_component × components; one-off = words × (languages − 1) × rate;
    each O&M year = one-off × annual_update_share × (1 + escalation_prices)^year."""
    tp = ctx.p.third_party
    if tp is None or tp.translation is None or ctx.q.languages <= 1 or not ctx.inp.components:
        return []
    n = sum(c.quantity for c in ctx.inp.components)

    def base(t: LineBuilder) -> Decimal:
        langs: int = t.driver("languages")
        per: Decimal = t.param("third_party", "translation", "words_per_component")
        rate = t.rate_local(t.param("third_party", "translation", "rate_key"))
        words = t.step("words to translate", f"{per} × {n} components", per * n)
        return t.step(
            "one-off translation", f"{words} × ({langs} − 1) × {rate}", words * (langs - 1) * rate
        )

    t = ctx.builder(
        line_key="build.content_translation/content",
        stage="build",
        bucket="build.content_translation",
        year=0,
        label="Content translation into other languages",
        formula_id="build.translation.v1",
    )
    one_off = base(t)
    spreads.clarity(t, ctx.overall_clarity())
    lines = [t.finish(one_off)]
    for year in range(1, ctx.q.om_years + 1):
        t = ctx.builder(
            line_key=f"{THIRD_PARTY_BUCKET}/translation_updates/y{year}",
            stage="run",
            bucket=THIRD_PARTY_BUCKET,
            year=year,
            label=f"Translation of new content (year {year})",
            formula_id="run.translation_updates.v1",
        )
        t.driver("om_years")
        one_off = base(t)
        share: Decimal = t.param("third_party", "translation", "annual_update_share")
        esc = t.escalation("prices", year)
        spreads.fixed(t, "fixed_fee")
        spreads.om_year(t, year)
        lines.append(t.finish(one_off * share * esc))
    return lines


# --- who pays ----------------------------------------------------------------------------------


def third_party_lines(ctx: PricingContext) -> list[CostLineOut]:
    """Usage-billed services in the quote: cloud-side services (firewall) when the vendor
    provides cloud hosting; the rest when usage fees are in scope. AI features' running cost
    is always in the quote, like the chatbot's."""
    tp = ctx.p.third_party
    if tp is None:
        return []
    cloud = [s for s in tp.services if s.needs_cloud_hosting]
    other = [s for s in tp.services if not s.needs_cloud_hosting]
    lines: list[CostLineOut] = []
    if ctx.q.hosting_in_scope and ctx.q.hosting_provider != "on_prem":
        lines += _services_lines(ctx, cloud)
    if ctx.q.usage_fees_in_scope:
        lines += _services_lines(ctx, other)
    return lines + ai_feature_lines(ctx)  # AI running cost is always part of the price


def client_paid_lines(ctx: PricingContext) -> list[CostLineOut]:
    """What the client pays providers directly (not in the quote): hosting they provide
    themselves (sized as if on the chosen cloud) and usage fees they take on."""
    tp = ctx.p.third_party
    if tp is None:
        return []
    if ctx.q.om_years == 0:
        return _after_handover(ctx, tp)
    lines: list[CostLineOut] = []
    if not ctx.q.hosting_in_scope:
        own = PricingContext(ctx.inp)
        own.q = ctx.q.model_copy(update={"hosting_in_scope": True})
        lines += hosting_lines(own)
        if ctx.q.hosting_provider != "on_prem":
            lines += _services_lines(own, [s for s in tp.services if s.needs_cloud_hosting])
        ctx.placeholders |= own.placeholders
    if not ctx.q.usage_fees_in_scope:
        lines += _services_lines(ctx, [s for s in tp.services if not s.needs_cloud_hosting])
    return lines


def _after_handover(ctx: PricingContext, tp: ThirdParty) -> list[CostLineOut]:
    """No support years: the client runs the system from launch, so one year of its running
    costs is shown for the client to budget — hosting, the chatbot's and AI features' usage,
    and usage-billed services — priced as if they were in scope for one year."""
    own = PricingContext(ctx.inp)
    own.q = ctx.q.model_copy(
        update={"om_years": 1, "hosting_in_scope": True, "usage_fees_in_scope": True}
    )
    lines = hosting_lines(own) + ai_runtime_lines(own) + ai_feature_lines(own)
    on_prem = ctx.q.hosting_provider == "on_prem"
    lines += _services_lines(
        own, [s for s in tp.services if not (on_prem and s.needs_cloud_hosting)]
    )
    ctx.placeholders |= own.placeholders
    return lines


def client_paid_notes(ctx: PricingContext) -> list[ClientPaidNoteOut]:
    """Rates the client pays per transaction (e.g. payment gateway fees), quoted as published."""
    tp = ctx.p.third_party
    if tp is None:
        return []
    notes = []
    for note in tp.client_paid_notes:
        if note.components and not set(note.components) & _in_scope(ctx):
            continue
        rates = []
        shown = []
        for key in note.rate_keys:
            item = ctx.rates[key]
            if item.source == PLACEHOLDER:
                ctx.placeholders.add(f"rate:{key}")
            rates.append(
                TraceRate(
                    key=item.key,
                    kind=item.kind.value,
                    unit=item.unit,
                    amount=item.amount,
                    currency=item.currency,
                    rate_card_version=ctx.inp.rate_card.version,
                    source=item.source,
                    source_url=item.source_url,
                )
            )
            if item.unit.startswith("ratio"):
                shown.append(f"{(item.amount * 100).normalize():f}%")
            else:
                shown.append(f"{item.currency} {item.amount:,.2f}")
        notes.append(
            ClientPaidNoteOut(
                key=note.key, label=note.label, text=note.text.format(*shown), rates=rates
            )
        )
    return notes

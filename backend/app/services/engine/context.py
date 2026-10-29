"""Pricing context and line builder.

`PricingContext` resolves questionnaire answers against defaults and gives typed access to
rates and parameters. `LineBuilder` records every rate, parameter, driver and intermediate
step a cost line touches, so the finished line carries its complete trace (rule 2).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Literal

from app.services.engine.formulas import FORMULAS
from app.services.engine.inputs import (
    QUESTIONNAIRE_KEYS,
    AnswerIn,
    ComponentInstanceIn,
    EstimateInput,
    Questionnaire,
    RequirementIn,
)
from app.services.engine.money import ONE, ZERO, dsum, interpolate, quantize, to_paise
from app.services.engine.outputs import (
    AssumptionOut,
    CostLineOut,
    LineTrace,
    Spread,
    SpreadFactor,
    TraceAnswer,
    TraceComponent,
    TraceParameter,
    TraceRate,
    TraceRequirement,
    TraceStep,
)
from app.services.engine.reference import PLACEHOLDER, CatalogComponent, RateItem

if TYPE_CHECKING:
    from app.services.engine.components import EffortPlan

SPREAD_QUANTUM = Decimal("0.0001")


@dataclass(frozen=True)
class ResolvedAnswer:
    key: str
    value: Any
    source: Literal["user", "default"]
    requirement_ids: tuple[str, ...]


def resolve_questionnaire(
    answers: list[AnswerIn], defaults: dict[str, object]
) -> tuple[Questionnaire, dict[str, ResolvedAnswer]]:
    """Merge user answers over parameter-set defaults and validate the result."""
    given = {a.key: a for a in answers}
    merged: dict[str, object] = {}
    resolved: dict[str, ResolvedAnswer] = {}
    for key in QUESTIONNAIRE_KEYS:
        if key in given:
            merged[key] = given[key].value
        elif key in defaults:
            merged[key] = defaults[key]
        elif not Questionnaire.model_fields[key].is_required():
            continue  # newer optional key absent from an older parameter set: model default
        else:
            raise ValueError(f"no answer and no default for questionnaire key {key!r}")
    questionnaire = Questionnaire.model_validate(merged)
    dumped = questionnaire.model_dump(mode="json")
    for key in QUESTIONNAIRE_KEYS:
        answer = given.get(key)
        resolved[key] = ResolvedAnswer(
            key=key,
            value=dumped[key],
            source="user" if answer is not None else "default",
            requirement_ids=tuple(answer.requirement_ids) if answer is not None else (),
        )
    return questionnaire, resolved


class PricingContext:
    def __init__(self, inp: EstimateInput) -> None:
        self.inp = inp
        self.p = inp.parameters
        self.q, self.answers = resolve_questionnaire(inp.answers, inp.parameters.defaults.values)
        self.requirements: dict[str, RequirementIn] = {r.id: r for r in inp.requirements}
        self.rates: dict[str, RateItem] = {i.key: i for i in inp.rate_card.items}
        self.placeholders: set[str] = set()
        if inp.taxonomy.source == PLACEHOLDER:
            self.placeholders.add("taxonomy")
        # the effort caps and project-wide reuse ratio (engine/components.py), worked out once
        # from every component on first use
        self.effort_plan: EffortPlan | None = None

    # --- convenience accessors -------------------------------------------------------------

    def months_per_year(self) -> Decimal:
        return self.p.calendar.pd_per_year / self.p.calendar.pd_per_month

    def overall_clarity(self) -> Decimal:
        """Mean clarity of the confirmed requirements; the parameter default if there are none."""
        scores = [Decimal(r.clarity_score) for r in self.inp.requirements]
        if not scores:
            return self.p.uncertainty.default_clarity
        return dsum(scores) / Decimal(len(scores))

    def component_clarity(self, ci: ComponentInstanceIn) -> Decimal:
        scores = [Decimal(self.requirements[r].clarity_score) for r in ci.requirement_ids]
        if not scores:
            return self.overall_clarity()
        return dsum(scores) / Decimal(len(scores))

    def _in_play(self, key: str) -> bool:
        """Whether a defaulted answer is worth a note. Answers added after estimates were
        saved, whose default keeps the earlier behaviour, are noted only when the parameter set
        uses them, so an older snapshot reprices to the identical result (rule 3)."""
        return {
            "disaster_recovery": False,  # default: no DR site, as before the answer existed
            "penalty_clause": self.p.commercial.penalty_needs_clause,
            "web_domain": bool(self.p.maintenance.domain_rate_key_by_type),
            "domain_in_scope": False,  # default: the vendor pays, as before the answer existed
            "ssl_in_scope": False,
            "ssl_type": bool(self.p.maintenance.ssl_rate_key_by_type),
            "ai_passthrough_percent": False,  # default: all passed through, as before
            "size_blend": False,  # set by the quick form near a size edge; never a note
        }.get(key, True)

    def assumptions(self) -> list[AssumptionOut]:
        out = []
        for key in QUESTIONNAIRE_KEYS:
            ans = self.answers[key]
            if ans.source == "default" and self._in_play(key):
                out.append(
                    AssumptionOut(
                        key=key,
                        text=f"No answer given for '{key}'; default {ans.value!r} assumed.",
                        value=ans.value,
                        overridden=False,
                    )
                )
        return out

    def builder(
        self,
        *,
        line_key: str,
        stage: str,
        bucket: str,
        year: int,
        label: str,
        formula_id: str,
        uncertainty_group: str | None = None,
    ) -> LineBuilder:
        if formula_id not in FORMULAS:
            raise KeyError(f"formula {formula_id} is not registered")
        self.inp.taxonomy.bucket(bucket)
        return LineBuilder(
            ctx=self,
            line_key=line_key,
            stage=stage,
            bucket=bucket,
            year=year,
            label=label,
            formula_id=formula_id,
            uncertainty_group=uncertainty_group or bucket,
        )


@dataclass
class LineBuilder:
    ctx: PricingContext
    line_key: str
    stage: str
    bucket: str
    year: int
    label: str
    formula_id: str
    uncertainty_group: str
    component: ComponentInstanceIn | None = None
    requirement_ids: list[str] = field(default_factory=list)
    drivers: dict[str, TraceAnswer] = field(default_factory=dict)
    rate_items: dict[str, TraceRate] = field(default_factory=dict)
    parameters: dict[str, TraceParameter] = field(default_factory=dict)
    steps: list[TraceStep] = field(default_factory=list)
    inputs: dict[str, object] = field(default_factory=dict)
    role_pd: dict[str, Decimal] = field(default_factory=dict)
    spread_factors: list[SpreadFactor] = field(default_factory=list)
    follows_build: bool = False  # see CostLineOut.follows_build

    # --- recording -------------------------------------------------------------------------

    def fork(self, **changes: Any) -> LineBuilder:
        """Copy this builder (with everything recorded so far) for a sibling line."""
        clone = LineBuilder(
            ctx=self.ctx,
            line_key=self.line_key,
            stage=self.stage,
            bucket=self.bucket,
            year=self.year,
            label=self.label,
            formula_id=self.formula_id,
            uncertainty_group=self.uncertainty_group,
            component=self.component,
            requirement_ids=list(self.requirement_ids),
            drivers=dict(self.drivers),
            rate_items=dict(self.rate_items),
            parameters=dict(self.parameters),
            steps=list(self.steps),
            inputs=dict(self.inputs),
        )
        for name, value in changes.items():
            setattr(clone, name, value)
        if "bucket" in changes and "uncertainty_group" not in changes:
            clone.uncertainty_group = changes["bucket"]
        self.ctx.inp.taxonomy.bucket(clone.bucket)
        if clone.formula_id not in FORMULAS:
            raise KeyError(f"formula {clone.formula_id} is not registered")
        return clone

    def link_component(self, ci: ComponentInstanceIn, catalog: CatalogComponent) -> None:
        self.component = ci
        if catalog.source == PLACEHOLDER:
            self.ctx.placeholders.add(f"catalog:{catalog.key}")
        for rid in ci.requirement_ids:
            if rid not in self.requirement_ids:
                self.requirement_ids.append(rid)

    def driver(self, key: str) -> Any:
        """Read a questionnaire driver and record it (and the requirements it cites)."""
        ans = self.ctx.answers[key]
        self.drivers[key] = TraceAnswer(
            key=key, value=ans.value, source=ans.source, requirement_ids=list(ans.requirement_ids)
        )
        for rid in ans.requirement_ids:
            if rid not in self.requirement_ids:
                self.requirement_ids.append(rid)
        return getattr(self.ctx.q, key)

    def param(self, *path: str | int) -> Any:
        """Read a parameter by attribute/key path and record it with its group's source (or the
        field's own, when the group lists it in `field_sources`)."""
        obj: Any = self.ctx.p
        source = self.ctx.p.complexity_source if path[0] == "complexity_multipliers" else ""
        own_source = False
        for part in path:
            overrides: dict[str, str] = getattr(obj, "field_sources", None) or {}
            if isinstance(obj, dict):
                obj = next(v for k, v in obj.items() if str(k) == str(part))
            elif isinstance(obj, list):
                obj = obj[int(part)]
            else:
                obj = getattr(obj, str(part))
            source = getattr(obj, "source", source)
            if str(part) in overrides:
                source, own_source = overrides[str(part)], True
        dotted = ".".join(str(p) for p in path)
        if source == PLACEHOLDER:
            self.ctx.placeholders.add(f"param:{dotted if own_source else path[0]}")
        value = obj.model_dump(mode="json") if hasattr(obj, "model_dump") else obj
        self.parameters[dotted] = TraceParameter(
            path=dotted,
            value=value,
            parameter_set_version=self.ctx.p.version,
            source=source or "unspecified",
        )
        return obj

    def rate(self, key: str) -> RateItem:
        try:
            item = self.ctx.rates[key]
        except KeyError as exc:
            raise KeyError(f"rate card {self.ctx.inp.rate_card.version} has no {key!r}") from exc
        if item.source == PLACEHOLDER:
            self.ctx.placeholders.add(f"rate:{key}")
        self.rate_items[key] = TraceRate(
            key=item.key,
            kind=item.kind.value,
            unit=item.unit,
            amount=item.amount,
            currency=item.currency,
            rate_card_version=self.ctx.inp.rate_card.version,
            source=item.source,
            source_url=item.source_url,
        )
        return item

    def rate_local(self, key: str) -> Decimal:
        """Rate amount in the estimate currency (the rate card's currency). An item priced in
        another currency is converted: amount × forex[item→card] × (1 + forex_buffer)."""
        item = self.rate(key)
        currency = self.ctx.inp.rate_card.currency
        if item.currency == currency:
            return item.amount
        forex_key: str = self.param("hosting", "forex_rate_key")
        fx = self.rate(f"{forex_key.split('.', 1)[0]}.{item.currency}_{currency}").amount
        buffer: Decimal = self.param("hosting", "forex_buffer")
        return self.step(
            f"{key} in {currency}",
            f"{item.amount} {item.currency} × {fx} × (1 + {buffer})",
            item.amount * fx * (ONE + buffer),
        )

    def calibration(self, dial: str) -> Decimal:
        """A calibration dial (effort_multiplier / run_multiplier); 1 when the set has none."""
        if self.ctx.p.calibration is None:
            return ONE
        value: Decimal = self.param("calibration", dial)
        segment_dials = {
            "effort_multiplier": self.ctx.p.calibration.segment_effort_multiplier,
            "run_multiplier": self.ctx.p.calibration.segment_run_multiplier,
        }[dial]
        segment = self.driver("buyer_segment")
        cal = self.ctx.p.calibration
        by_size = (
            cal.segment_size_effort_multiplier.get(segment, {})
            if dial == "effort_multiplier"
            else {}
        )
        size_key = self.driver("project_size") if by_size else None
        if size_key in by_size:
            factor: Decimal = self.param(
                "calibration", "segment_size_effort_multiplier", segment, str(size_key)
            )
            value = self.step(
                f"{dial} × {segment} factor ({size_key} projects)",
                f"{value} × {factor}",
                value * factor,
            )
        elif segment in segment_dials:
            factor = self.param("calibration", f"segment_{dial}", segment)
            value = self.step(f"{dial} × {segment} factor", f"{value} × {factor}", value * factor)
        sizes = self.ctx.p.calibration.size_effort_multiplier
        curve = self.ctx.p.calibration.size_points_curve
        points = self.driver("size_points") if dial == "effort_multiplier" and curve else None
        if points is not None:
            self.param("calibration", "size_points_curve")
            f_pts = interpolate(curve, Decimal(points))
            value = self.step(
                f"{dial} × size factor at {points} feature points",
                f"{value} × {f_pts:.4f}",
                value * f_pts,
            )
        elif dial == "effort_multiplier" and sizes:
            size = self.driver("project_size")
            if size in sizes:
                f: Decimal = self.param("calibration", "size_effort_multiplier", size)
                value = self.step(f"{dial} × {size} project", f"{value} × {f}", value * f)
        if dial == "effort_multiplier":
            for key, by_value in self.ctx.p.calibration.answer_effort_multiplier.items():
                answer = str(self.driver(key))
                if answer in by_value:
                    g: Decimal = self.param("calibration", "answer_effort_multiplier", key, answer)
                    value = self.step(f"{dial} × {key} {answer}", f"{value} × {g}", value * g)
        return value

    def token_rates(self) -> tuple[Decimal, Decimal]:
        """(input, output) price per token unit for the chosen AI model tier, in the estimate
        currency. The simple tier applies only when the parameter set prices one."""
        keys = ("token_input_rate_key", "token_output_rate_key")
        rt = self.ctx.p.ai_runtime
        has_simple = bool(rt.simple_token_input_rate_key and rt.simple_token_output_rate_key)
        if has_simple and self.driver("ai_model_tier") == "simple":
            keys = ("simple_token_input_rate_key", "simple_token_output_rate_key")
        p_in = self.rate_local(self.param("ai_runtime", keys[0]))
        p_out = self.rate_local(self.param("ai_runtime", keys[1]))
        return p_in, p_out

    def lean(self) -> Decimal:
        """How much of the delivery is lean (recorded): 1 when the parameter set has lean
        delivery for this buyer segment or project size, or no formal reports and meetings
        (unless_governance); 0 when not. Near the edge of a lean and a full project size
        (size_blend, OPEN_QUESTIONS 184): (1 − share) × [own size lean] + share × [neighbour
        lean], so a lean line moves in a line from lean to full: full − lean × (full − lean
        value)."""
        lean = self.ctx.p.lean
        if lean is None:
            return ZERO
        segment: str = self.driver("buyer_segment")
        if segment in lean.segments:
            self.param("lean", "segments")
            return ONE
        by_size = ZERO
        if lean.sizes:
            own = ONE if self.driver("project_size") in lean.sizes else ZERO
            blend = self.ctx.q.size_blend
            by_size = own
            if blend is not None:
                self.driver("size_blend")
                near = ONE if blend.size in lean.sizes else ZERO
                by_size = self.step(
                    "lean share",
                    f"(1 − {blend.share}) × {own} + {blend.share} × {near} ({blend.size})",
                    (ONE - blend.share) * own + blend.share * near,
                )
            if by_size:
                self.param("lean", "sizes")
            if by_size == ONE:
                return ONE
        if lean.unless_governance and not self.driver("governance_overheads"):
            self.param("lean", "unless_governance")
            return ONE
        return by_size

    def step(self, label: str, expression: str, value: Decimal) -> Decimal:
        self.steps.append(TraceStep(label=label, expression=expression, value=value))
        return value

    def add_input(self, **values: object) -> None:
        self.inputs.update(values)

    def add_role_pd(self, role: str, pd: Decimal) -> None:
        self.role_pd[role] = self.role_pd.get(role, ZERO) + pd

    def spread(self, name: str, down: Decimal, up: Decimal) -> None:
        self.spread_factors.append(SpreadFactor(name=name, down=down, up=up))

    def escalation(self, kind: str, year: int) -> Decimal:
        """(1 + escalation)^year for kind 'labour' or 'prices'; questionnaire overrides params."""
        override = self.driver(f"escalation_{kind}")
        rate: Decimal = override if override is not None else self.param("escalation", kind)
        return self.step(
            f"escalation ({kind}) year {year}", f"(1 + {rate})^{year}", (ONE + rate) ** year
        )

    # --- finishing -------------------------------------------------------------------------

    def finish(
        self, likely_rupees: Decimal, *, derived: bool = False, gst_percent: Decimal | None = None
    ) -> CostLineOut:
        down = min(ONE, sum((f.down for f in self.spread_factors), ZERO))
        up = sum((f.up for f in self.spread_factors), ZERO)
        likely = to_paise(likely_rupees)
        low = to_paise(likely_rupees * (ONE - down))
        high = to_paise(likely_rupees * (ONE + up))
        return self._line(likely, low, high, down, up, derived, gst_percent)

    def finish_three_point(
        self, low: Decimal, likely: Decimal, high: Decimal, *, gst_percent: Decimal | None = None
    ) -> CostLineOut:
        """Finish a derived line whose three points were computed directly."""
        return self._line(
            to_paise(likely), to_paise(low), to_paise(high), ZERO, ZERO, True, gst_percent
        )

    def _line(
        self,
        likely: int,
        low: int,
        high: int,
        down: Decimal,
        up: Decimal,
        derived: bool,
        gst_percent: Decimal | None,
    ) -> CostLineOut:
        bucket = self.ctx.inp.taxonomy.bucket(self.bucket)
        if gst_percent is None:
            gst_percent = bucket.gst_percent
        if gst_percent is None:
            override = self.ctx.q.gst_percent
            gst_percent = override if override is not None else self.ctx.p.commercial.gst_percent
        reqs = [
            self.ctx.requirements[r] for r in self.requirement_ids if r in self.ctx.requirements
        ]
        comp = None
        if self.component is not None:
            cat = self.ctx.inp.catalog.get(self.component.catalog_key)
            comp = TraceComponent(
                id=self.component.id,
                catalog_key=cat.key,
                name=self.component.label or cat.name,
                size=self.component.size.value,
                complexity=self.component.complexity.value,
                quantity=self.component.quantity,
            )
        trace = LineTrace(
            requirements=[
                TraceRequirement(
                    id=r.id,
                    code=r.code,
                    text=r.text,
                    clause_ref=r.source_refs[0].clause_ref if r.source_refs else None,
                    page=r.source_refs[0].page if r.source_refs else None,
                )
                for r in reqs
            ],
            component=comp,
            drivers=list(self.drivers.values()),
            rate_items=list(self.rate_items.values()),
            parameters=list(self.parameters.values()),
            formula_id=self.formula_id,
            formula=FORMULAS[self.formula_id],
            steps=self.steps,
            spread=Spread(
                down=quantize(down, SPREAD_QUANTUM),
                up=quantize(up, SPREAD_QUANTUM),
                factors=self.spread_factors,
            ),
        )
        return CostLineOut(
            line_key=self.line_key,
            stage=self.stage,
            bucket=self.bucket,
            year=self.year,
            label=self.label,
            component_instance_id=self.component.id if self.component else None,
            formula_id=self.formula_id,
            inputs=self.inputs,
            low_paise=low,
            likely_paise=likely,
            high_paise=high,
            requirement_ids=[r.id for r in reqs],
            uncertainty_group=self.uncertainty_group,
            derived=derived,
            gst_percent=gst_percent,
            role_pd=self.role_pd,
            trace=trace,
            follows_build=self.follows_build,
        )


def toward_lean(
    t: LineBuilder, label: str, full: Decimal, lean: Decimal, share: Decimal
) -> Decimal:
    """full − share × (full − lean): the lean value when share is 1, in a line between the two
    near the edge of a lean and a full project size (OPEN_QUESTIONS 184)."""
    if share == ONE:
        return lean
    return t.step(
        f"{label} between full and lean",
        f"{full:.2f} − {share} × ({full:.2f} − {lean:.2f})",
        full - share * (full - lean),
    )

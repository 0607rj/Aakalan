"""Three-point spread rules (brief 7.2). Each rule adds a named factor to a line, so the trace
explains why its optimistic / pessimistic values sit where they do."""

from decimal import Decimal

from app.services.engine.context import LineBuilder
from app.services.engine.money import ONE, ZERO, quantize


def clarity(t: LineBuilder, clarity_score: Decimal) -> None:
    """Base spread from requirement clarity (1 = vague … 5 = precise), rounded half up."""
    bucket = int(quantize(clarity_score, ONE))
    s = t.param("uncertainty", "clarity_spread", bucket)
    t.spread(f"clarity {clarity_score:.2f}", s.down, s.up)


def template_match(t: LineBuilder) -> None:
    match = t.ctx.inp.template_match
    extra: Decimal = t.param("uncertainty", "template_match_extra_up", match)
    if extra:
        t.spread(f"template match: {match}", ZERO, extra)


def tags(t: LineBuilder, tag_names: list[str]) -> None:
    for tag in tag_names:
        extra: Decimal = t.param("uncertainty", "tag_extra_up", tag)
        t.spread(f"{tag} unknowns", ZERO, extra)


def hard_problem(t: LineBuilder) -> None:
    """A component holding a hard problem (v19+): extra down and up spread, so the range widens
    while the planned cost stays the same."""
    s = t.ctx.p.uncertainty.hard_problem_extra
    if s is not None:
        t.param("uncertainty", "hard_problem_extra")
        t.spread("hard problem", s.down, s.up)


def compression(t: LineBuilder, multiplier: Decimal) -> None:
    if multiplier > ONE:
        per_unit: Decimal = t.param("uncertainty", "compression_extra_up_per_unit")
        t.spread("schedule compression", ZERO, (multiplier - ONE) * per_unit)


def om_year(t: LineBuilder, year: int) -> None:
    if year > 1:
        per_year: Decimal = t.param("uncertainty", "om_extra_up_per_year")
        t.spread(f"O&M year {year}", ZERO, per_year * (year - 1))


def fixed(t: LineBuilder, name: str) -> None:
    """Named spread from the parameter set: 'hosting', 'ai_runtime' or 'fixed_fee'."""
    s = t.param("uncertainty", name)
    t.spread(name.replace("_", " "), s.down, s.up)

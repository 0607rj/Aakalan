"""Money and Decimal helpers. All deterministic engine arithmetic is Decimal; values are
rounded to integer paise (ROUND_HALF_UP) once, at the cost-line boundary (rule 5)."""

from collections.abc import Iterable, Sequence
from decimal import ROUND_CEILING, ROUND_HALF_UP, Context, Decimal
from itertools import pairwise

from app.services.engine.reference import Point

PAISE_PER_RUPEE = Decimal(100)  # unit definition, not a tunable parameter
ENGINE_CONTEXT = Context(prec=28, rounding=ROUND_HALF_UP)
ONE = Decimal(1)
ZERO = Decimal(0)


def to_paise(rupees: Decimal) -> int:
    """Round rupees to whole paise, half up."""
    return int((rupees * PAISE_PER_RUPEE).quantize(ONE, rounding=ROUND_HALF_UP))


def paise_to_rupees(paise: int) -> Decimal:
    return Decimal(paise) / PAISE_PER_RUPEE


def float_to_paise(value: float) -> int:
    """Round a simulated float (already in paise) to whole paise, half up, exactly."""
    return int(Decimal(value).quantize(ONE, rounding=ROUND_HALF_UP))


def ceil(value: Decimal) -> Decimal:
    return value.to_integral_value(rounding=ROUND_CEILING)


def quantize(value: Decimal, quantum: Decimal) -> Decimal:
    return value.quantize(quantum, rounding=ROUND_HALF_UP)


def ceil_to(value: Decimal, quantum: Decimal) -> Decimal:
    return value.quantize(quantum, rounding=ROUND_CEILING)


def dsum(values: Iterable[Decimal]) -> Decimal:
    return sum(values, ZERO)


def interpolate(points: Sequence[Point], x: Decimal, *, extrapolate: bool = False) -> Decimal:
    """Piecewise-linear interpolation through `points` (sorted by x here).

    Outside the range: clamp to the end value, or extend the nearest segment if `extrapolate`.
    """
    pts = sorted(points, key=lambda p: p.x)
    if len(pts) == 1:
        return pts[0].y
    if x <= pts[0].x:
        lo, hi = pts[0], pts[1]
        if not extrapolate:
            return lo.y
    elif x >= pts[-1].x:
        lo, hi = pts[-2], pts[-1]
        if not extrapolate:
            return hi.y
    else:
        lo, hi = next((a, b) for a, b in pairwise(pts) if a.x <= x <= b.x)
    return lo.y + (hi.y - lo.y) * (x - lo.x) / (hi.x - lo.x)

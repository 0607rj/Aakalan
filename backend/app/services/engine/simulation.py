"""Seeded Monte Carlo over three-point line values (brief 7.2).

- Each *uncertainty group* (a component instance, or a run/programme bucket) gets its own
  quantile stream from `numpy.random.default_rng([seed, sha256(group)])`, so all lines in a
  group move together and adding scope never re-shuffles other groups' draws.
- Each base line maps the shared quantile through its triangular(low, likely, high) inverse CDF.
- Derived commercial lines are recomputed per run with `commercial.derived_amounts`.
- Floats live only inside this module; results are rounded to paise at the boundary.
"""

import hashlib
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal

import numpy as np
from numpy.typing import NDArray

from app.services.engine.commercial import BaseSums, Factors, derived_amounts
from app.services.engine.money import float_to_paise
from app.services.engine.outputs import CostLineOut, RangeDriver
from app.services.engine.reference import Taxonomy

PERCENTILES = (10.0, 50.0, 90.0)  # definition of the reported P10 / P50 / P90
SHARE_QUANTUM = Decimal("0.001")

FloatArray = NDArray[np.float64]


def group_quantiles(seed: int, group: str, runs: int) -> FloatArray:
    digest = int.from_bytes(hashlib.sha256(group.encode("utf-8")).digest()[:8], "big")
    rng = np.random.default_rng([seed, digest])
    return rng.random(runs)


def triangular_inverse(u: FloatArray, low: float, mode: float, high: float) -> FloatArray:
    """Inverse CDF of triangular(low, mode, high) evaluated at quantiles u."""
    if high <= low:
        return np.full_like(u, mode)
    span = high - low
    f_mode = (mode - low) / span
    left = low + np.sqrt(u * span * (mode - low))
    right = high - np.sqrt((1.0 - u) * span * (high - mode))
    result: FloatArray = np.where(u < f_mode, left, right)
    return result


@dataclass(frozen=True)
class SimulationResult:
    p10_paise: int
    p50_paise: int
    p90_paise: int
    drivers: list[RangeDriver]


def simulate(
    lines: Sequence[CostLineOut],
    factors: Factors,
    seed: int,
    runs: int,
    taxonomy: Taxonomy,
) -> SimulationResult:
    base = [line for line in lines if not line.derived]
    quantiles: dict[str, FloatArray] = {}
    zeros = np.zeros(runs, dtype=np.float64)
    total, build, run = zeros.copy(), zeros.copy(), zeros.copy()
    by_rate: dict[Decimal, FloatArray] = defaultdict(lambda: zeros.copy())
    by_bucket: dict[str, FloatArray] = defaultdict(lambda: zeros.copy())
    for line in base:
        group = line.uncertainty_group
        if group not in quantiles:
            quantiles[group] = group_quantiles(seed, group, runs)
        x = triangular_inverse(
            quantiles[group],
            float(line.low_paise),
            float(line.likely_paise),
            float(line.high_paise),
        )
        total += x
        if line.year == 0 and line.stage != "commercial":
            build += x
        elif line.year > 0:
            run += x
        by_rate[line.gst_percent] += x
        by_bucket[line.bucket] += x

    float_factors = factors.map(float)
    derived = derived_amounts(
        BaseSums(total, build, run, dict(by_rate)), float_factors, lambda r: float(r)
    )
    grand = total + sum(derived.values(), zeros)
    p10, p50, p90 = np.percentile(grand, PERCENTILES)
    return SimulationResult(
        p10_paise=float_to_paise(float(p10)),
        p50_paise=float_to_paise(float(p50)),
        p90_paise=float_to_paise(float(p90)),
        drivers=range_drivers(by_bucket, taxonomy),
    )


def range_drivers(by_bucket: dict[str, FloatArray], taxonomy: Taxonomy) -> list[RangeDriver]:
    """Share of the base-cost variance contributed by each bucket. Groups never span buckets
    and are independent, so bucket variances add up to the total base variance."""
    variances = {b: float(np.var(v)) for b, v in by_bucket.items()}
    total = sum(variances.values())
    if total <= 0:
        return []
    out = [
        RangeDriver(
            bucket=b,
            name=f"{taxonomy.bucket(b).stage.replace('_', '-').capitalize()}: "
            f"{taxonomy.bucket(b).name.lower()}",
            variance_share=Decimal(var / total).quantize(SHARE_QUANTUM),
        )
        for b, var in variances.items()
    ]
    out.sort(key=lambda d: (-d.variance_share, d.bucket))
    return out

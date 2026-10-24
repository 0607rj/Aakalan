"""Seeded Monte Carlo over three-point line values (brief 7.2).

- Each *uncertainty group* (a component instance, or a run/programme bucket) gets its own
  quantile stream from `numpy.random.default_rng([seed, sha256(group)])`, so all lines in a
  group move together and adding scope never re-shuffles other groups' draws.
- Each base line maps the shared quantile through its triangular(low, likely, high) inverse CDF.
- An optional shared model-error factor (back-test residuals) multiplies every base line in a
  run by one draw of triangular(1 − down, 1, 1 + up): estimation error is systematic, so it
  does not average out across groups the way independent group noise does. Centred on its
  median (parameter sets v23+), each draw is divided by the triangle's median, so the factor
  widens the range without moving P50 (OPEN_QUESTIONS 160).
- Derived commercial lines are recomputed per run with `commercial.derived_amounts`.
- Range drivers rank buckets by their own variance, leaving out lines that follow the build;
  the shared factor, when named, is a driver of its own (its share of the base variance).
- Floats live only inside this module; results are rounded to paise at the boundary.
"""

import hashlib
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass, replace
from decimal import Decimal

import numpy as np
from numpy.typing import NDArray

from app.services.engine.commercial import BaseSums, Factors, derived_amounts
from app.services.engine.money import float_to_paise, to_paise
from app.services.engine.outputs import CostLineOut, RangeDriver
from app.services.engine.reference import Taxonomy

PERCENTILES = (10.0, 50.0, 90.0)  # definition of the reported P10 / P50 / P90
SHARE_QUANTUM = Decimal("0.001")
MODEL_GROUP = "__model_error__"
MODEL_DRIVER = "model_error"  # RangeDriver.bucket of the shared model-error factor

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
    model_spread: tuple[Decimal, Decimal] | None = None,
    model_centre: str = "mode",
    model_name: str = "",
) -> SimulationResult:
    base = [line for line in lines if not line.derived]
    quantiles: dict[str, FloatArray] = {}
    zeros = np.zeros(runs, dtype=np.float64)
    model = np.ones(runs, dtype=np.float64)
    if model_spread is not None:
        down, up = (float(v) for v in model_spread)
        model = triangular_inverse(group_quantiles(seed, MODEL_GROUP, runs), 1 - down, 1.0, 1 + up)
        if model_centre == "median":
            half = np.array([0.5], dtype=np.float64)
            model = model / float(triangular_inverse(half, 1 - down, 1.0, 1 + up)[0])
    plain = zeros.copy()  # the base total before the shared factor (range drivers)
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
        if not line.follows_build:  # range drivers: sources of their own uncertainty only
            by_bucket[line.bucket] += x
        plain += x
        x = x * model
        total += x
        if line.year == 0 and line.stage != "commercial":
            build += x
        elif line.year > 0:
            run += x
        by_rate[line.gst_percent] += x

    # the runs add up paise: the AI saving kept (a fixed amount in rupees) is converted to paise
    float_factors = replace(factors.map(float), ai_kept=float(to_paise(factors.ai_kept)))
    derived = derived_amounts(
        BaseSums(total, build, run, dict(by_rate)), float_factors, lambda r: float(r)
    )
    grand = total + sum(derived.values(), zeros)
    p10, p50, p90 = np.percentile(grand, PERCENTILES)
    return SimulationResult(
        p10_paise=float_to_paise(float(p10)),
        p50_paise=float_to_paise(float(p50)),
        p90_paise=float_to_paise(float(p90)),
        drivers=range_drivers(
            by_bucket,
            taxonomy,
            _model_share(plain, model) if model_spread and model_name else None,
            model_name,
        ),
    )


def _model_share(plain: FloatArray, model: FloatArray) -> float:
    """The shared factor's share of the base variance: 1 − mean(f)² × var(B) / var(f × B), where
    B is the base total before the factor (what would be left with the factor held at its
    mean)."""
    total = float(np.var(plain * model))
    if total <= 0:
        return 0.0
    return min(1.0, max(0.0, 1.0 - float(np.mean(model)) ** 2 * float(np.var(plain)) / total))


def range_drivers(
    by_bucket: dict[str, FloatArray],
    taxonomy: Taxonomy,
    model_share: float | None = None,
    model_name: str = "",
) -> list[RangeDriver]:
    """Share of the base-cost variance contributed by each bucket. Groups never span buckets
    and are independent, so bucket variances add up to the total base variance. Lines whose
    amount follows the build (project management, support as a share of the build) are left
    out: their spread is a consequence of the build's, not an unknown of its own. With a shared
    model-error factor, it is a driver with its share (`_model_share`) and the buckets share the
    rest in proportion to their variances."""
    variances = {b: float(np.var(v)) for b, v in by_bucket.items()}
    total = sum(variances.values())
    rest = 1.0 if model_share is None else 1.0 - model_share
    out = []
    if model_share:
        out.append(
            RangeDriver(
                bucket=MODEL_DRIVER,
                name=model_name or "Model error",
                variance_share=Decimal(model_share).quantize(SHARE_QUANTUM),
            )
        )
    if total <= 0:
        return out
    out += [
        RangeDriver(
            bucket=b,
            name=f"{taxonomy.bucket(b).stage.replace('_', '-').capitalize()}: "
            f"{taxonomy.bucket(b).name.lower()}",
            variance_share=Decimal(rest * var / total).quantize(SHARE_QUANTUM),
        )
        for b, var in variances.items()
    ]
    out.sort(key=lambda d: (-d.variance_share, d.bucket))
    return out

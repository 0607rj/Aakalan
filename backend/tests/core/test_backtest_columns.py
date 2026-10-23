"""Back-test columns: contracts priced before AI tools are judged on our price without them."""

from decimal import Decimal
from typing import Any

import pytest

from app.services.calibration.backtest import (
    BacktestRow,
    Benchmark,
    BenchmarkSet,
    band_ratio,
    on_column,
    overlaps,
    scaled,
    segment_metrics,
)


def bench(year: int, **extra: Any) -> Benchmark:
    return Benchmark.model_validate(
        {
            "id": f"p{year}",
            "title": "t",
            "award_year": year,
            "value_minor": 100,
            "source_url": "https://example.org",
            "confidence": "high",
            "use": True,
            "model": {"scale": "small", "om_years": 0},
            **extra,
        }
    )


def test_pre_ai_by_award_year_unless_flagged() -> None:
    s = BenchmarkSet(country="india", currency="INR", pre_ai_until=2024, projects=[])
    assert s.is_pre_ai(bench(2022)) and s.is_pre_ai(bench(2024))
    assert not s.is_pre_ai(bench(2025))
    assert not s.is_pre_ai(bench(2022, pre_ai=False))  # the project's own flag wins
    assert not BenchmarkSet(country="india", currency="INR", projects=[]).is_pre_ai(bench(2010))


def row(ratio_with: float, ratio_pre: float, pre_ai: bool) -> BacktestRow:
    judged = ratio_pre if pre_ai else ratio_with
    return BacktestRow(
        id="x",
        title="t",
        use=True,
        buyer="government",
        published_minor=100,
        published_high_minor=None,
        estimate_minor=int(judged * 100),
        ratio=judged,
        error_percent=round((judged - 1) * 100, 1),
        size="large",
        pre_ai=pre_ai,
        ratio_with_ai=ratio_with,
        ratio_pre_ai=ratio_pre,
        inside_range=True,
    )


def test_each_column_is_measured_on_its_own_ratio() -> None:
    rows = [row(0.8, 0.9, True), row(1.0, 1.2, False)]
    judged = segment_metrics(rows, "all")[0]
    assert judged.median_abs_error_percent == 5.0  # |0.9 - 1| and |1.0 - 1|
    with_ai = segment_metrics(on_column(rows, "with_ai"), "all")[0]
    assert with_ai.median_abs_error_percent == 10.0  # 20% and 0%
    pre_ai = segment_metrics(on_column(rows, "pre_ai"), "all")[0]
    assert pre_ai.median_abs_error_percent == 15.0 and pre_ai.inside_range == 0


def test_with_ai_is_scored_against_the_expected_saving() -> None:
    """Round 3: with AI tools against published × 0.75-0.80 (inside counts as exact)."""
    inside = row(0.78, 1.0, True).model_copy(
        update={"ratio_ai_target": band_ratio(78, 75, 80), "inside_range_ai_target": True}
    )
    above = row(1.0, 1.25, True).model_copy(
        update={"ratio_ai_target": band_ratio(100, 75, 80), "inside_range_ai_target": False}
    )
    scored = segment_metrics(on_column([inside, above], "ai_target"), "all")[0]
    assert inside.ratio_ai_target == 1.0
    assert above.ratio_ai_target == 1.25  # measured to the nearer edge, 100 / 80
    assert scored.within_25_percent == 2 and scored.inside_range == 1


def test_coverage_is_checked_against_each_columns_target() -> None:
    assert overlaps((70, 90, 120), 100, None)  # P10-P90 70-120 contains 100
    assert not overlaps((70, 80, 90), 100, None)
    assert overlaps((70, 74, 76), scaled(100, Decimal("0.75")), scaled(100, Decimal("0.80")))


def test_a_project_left_out_names_its_rule() -> None:
    out = {"use": False, "reason": "staff by the month"}
    assert bench(2024, **out, exclude_rule="staffing").exclude_rule == "staffing"
    with pytest.raises(ValueError):
        bench(2024, **out)  # no rule
    with pytest.raises(ValueError):
        bench(2024, exclude_rule="staffing")  # used, yet excluded

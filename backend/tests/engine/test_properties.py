"""Property tests (brief Section 13): more scope never lowers cost; lower clarity never narrows
the range; a shorter deadline (at or below natural duration) never lowers cost."""

from collections.abc import Callable
from decimal import Decimal

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from app.services.engine.core import calculate
from app.services.engine.inputs import EstimateInput
from app.services.engine.outputs import EstimateResult
from tests.engine.conftest import answer, tweak

RUNS = 1000
PROPERTY_SETTINGS = settings(
    max_examples=12, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture]
)


def fast(inp: EstimateInput) -> EstimateInput:
    return inp.model_copy(update={"monte_carlo_runs": RUNS})


def totals(result: EstimateResult) -> tuple[int, ...]:
    assert result.totals is not None
    t = result.totals
    return (
        t.low_sum_paise,
        t.likely_paise,
        t.high_sum_paise,
        t.p10_paise,
        t.p50_paise,
        t.p90_paise,
    )


@PROPERTY_SETTINGS
@given(data=st.data())
def test_more_scope_never_lowers_cost(
    golden: Callable[[str], EstimateInput], data: st.DataObject
) -> None:
    base = fast(golden("small"))
    keys = [c.key for c in base.catalog.components]
    key = data.draw(st.sampled_from(keys))
    size = data.draw(st.sampled_from(["S", "M", "L"]))
    quantity = data.draw(st.integers(min_value=1, max_value=3))
    extra = {"id": "extra", "catalog_key": key, "size": size, "quantity": quantity}
    bigger = tweak(base, components=[*[c.model_dump() for c in base.components], extra])
    before, after = totals(calculate(base)), totals(calculate(bigger))
    assert all(a >= b for a, b in zip(after, before, strict=True)), (key, before, after)


@PROPERTY_SETTINGS
@given(index=st.integers(min_value=0, max_value=10), data=st.data())
def test_larger_component_never_lowers_cost(
    golden: Callable[[str], EstimateInput], index: int, data: st.DataObject
) -> None:
    base = fast(golden("small"))
    comps = [c.model_dump() for c in base.components]
    order = ["S", "M", "L"]
    current = order.index(comps[index]["size"])
    if current == 2:
        comps[index]["quantity"] += 1
    else:
        comps[index]["size"] = data.draw(st.sampled_from(order[current + 1 :]))
    before, after = totals(calculate(base)), totals(calculate(tweak(base, components=comps)))
    assert all(a >= b for a, b in zip(after, before, strict=True))


@PROPERTY_SETTINGS
@given(name=st.sampled_from(["small", "medium"]), drop=st.integers(min_value=1, max_value=3))
def test_lower_clarity_never_narrows_range(
    golden: Callable[[str], EstimateInput], name: str, drop: int
) -> None:
    base = fast(golden(name))
    vaguer = tweak(
        base,
        requirements=[
            {**r.model_dump(), "clarity_score": max(1, r.clarity_score - drop)}
            for r in base.requirements
        ],
    )
    b, v = calculate(base).totals, calculate(vaguer).totals
    assert b is not None and v is not None
    assert v.p90_paise - v.p10_paise >= b.p90_paise - b.p10_paise
    assert v.high_sum_paise - v.low_sum_paise >= b.high_sum_paise - b.low_sum_paise


@PROPERTY_SETTINGS
@given(
    name=st.sampled_from(["small", "medium", "large"]),
    hi=st.decimals(min_value=Decimal("0.51"), max_value=Decimal("1.0"), places=2),
    gap=st.decimals(min_value=Decimal("0.01"), max_value=Decimal("0.4"), places=2),
)
def test_shorter_deadline_never_lowers_cost(
    golden: Callable[[str], EstimateInput], name: str, hi: Decimal, gap: Decimal
) -> None:
    base = fast(answer(golden(name), "deadline_months", None))
    natural = calculate(base).timeline.natural_duration_months
    lo = max(Decimal("0.5"), hi - gap)
    longer = calculate(answer(base, "deadline_months", str(natural * hi)))
    shorter = calculate(answer(base, "deadline_months", str(natural * lo)))
    if not shorter.feasible:
        return
    assert all(s >= g for s, g in zip(totals(shorter), totals(longer), strict=True))

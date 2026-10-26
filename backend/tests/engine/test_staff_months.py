"""Staff for part of the support period and round-the-clock seats (OPEN_QUESTIONS 162):
maintenance.onsite.v2 / maintenance.support_staff.v2."""

from collections.abc import Callable
from decimal import Decimal

import pytest

from app.services.engine.core import calculate
from app.services.engine.formulas import FORMULAS
from app.services.engine.inputs import EstimateInput
from app.services.seeding.reference import ReferenceData
from tests.engine.conftest import answer, tweak

D = Decimal


@pytest.fixture
def v24(golden: Callable[[str], EstimateInput], reference: ReferenceData) -> EstimateInput:
    """The small golden project on parameters v24 with 5 support years."""
    inp = tweak(
        golden("small"),
        taxonomy=reference.taxonomy,
        catalog=reference.catalog_version("v5"),
        rate_card=reference.rate_card("v9"),
        parameters=reference.parameter_set("v24"),
    )
    return answer(inp, "om_years", 5)


def staff_pd(inp: EstimateInput) -> dict[int, Decimal]:
    """Person-days of the staff lines, by support year."""
    out: dict[int, Decimal] = {}
    for ln in calculate(inp).lines:
        if ln.bucket == "run.onsite_resources":
            out[ln.year] = out.get(ln.year, D(0)) + sum(ln.role_pd.values(), D(0))
    return out


def test_staff_for_part_of_the_support_period(v24: EstimateInput) -> None:
    """18 months over 5 support years: a full year 1, half of year 2, nothing after."""
    pd_year = v24.parameters.calendar.pd_per_year
    res = {"role": "role.developer", "count": 2, "months": 18, "name": "developers at HO"}
    by_year = staff_pd(answer(v24, "onsite_resources", [res]))
    assert by_year == {1: 2 * pd_year, 2: pd_year}
    lines = [ln for ln in calculate(answer(v24, "onsite_resources", [res])).lines if ln.year == 2]
    line = next(ln for ln in lines if ln.bucket == "run.onsite_resources")
    assert line.formula_id == "maintenance.onsite.v2" and "developers at HO" in line.label
    assert "maintenance.onsite.v2" in FORMULAS and "maintenance.support_staff.v2" in FORMULAS


def test_round_the_clock_seats_use_people_per_seat(v24: EstimateInput) -> None:
    """A committed team of 1 per shift round the clock: 1 seat × 4.0 people (v24), traced."""
    per_seat = v24.parameters.maintenance.helpdesk_coverage_fte["24x7"]
    assert per_seat == D("4.0")
    pd_year = v24.parameters.calendar.pd_per_year
    seat = {"role": "role.developer", "count": 1, "seats": True}
    by_year = staff_pd(answer(v24, "onsite_resources", [seat]))
    assert all(pd == per_seat * pd_year for pd in by_year.values()) and len(by_year) == 5
    line = next(
        ln
        for ln in calculate(answer(v24, "onsite_resources", [seat])).lines
        if ln.bucket == "run.onsite_resources"
    )
    assert any("people per seat" in s.label for s in line.trace.steps)


def test_staff_without_months_or_seats_keep_the_v1_formula(v24: EstimateInput) -> None:
    res = {"role": "role.developer", "count": 1}
    lines = calculate(answer(v24, "onsite_resources", [res])).lines
    assert {ln.formula_id for ln in lines if ln.bucket == "run.onsite_resources"} == {
        "maintenance.onsite.v1"
    }


def test_support_staff_for_part_of_the_period_are_the_least_support_labour(
    v24: EstimateInput,
) -> None:
    """Support staff for 12 months add only their shortfall in year 1, nothing later."""
    big = {"role": "role.developer", "count": 20, "kind": "support", "months": 12}
    by_year = staff_pd(answer(v24, "onsite_resources", [big]))
    assert set(by_year) == {1} and by_year[1] > 0

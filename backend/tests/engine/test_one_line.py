"""Simpler lines and no double charges (parameter sets v25+, OPEN_QUESTIONS 166): hosting and
upkeep as one line a year, stated onsite staff doing the upkeep / O&M project management, the
annual re-audit from support year 2, and the hypercare weeks not priced again in year 1."""

from collections.abc import Callable
from decimal import Decimal

import pytest

from app.services.engine.core import calculate
from app.services.engine.formulas import FORMULAS
from app.services.engine.inputs import EstimateInput
from app.services.engine.outputs import CostLineOut
from app.services.seeding.reference import ReferenceData
from tests.engine.conftest import answer, tweak

D = Decimal


def project(
    golden: Callable[[str], EstimateInput],
    reference: ReferenceData,
    params: str = "v25",
    rates: str = "v10",
) -> EstimateInput:
    """The small golden project on AWS with 3 support years, a security audit and no hypercare."""
    inp = tweak(
        golden("small"),
        taxonomy=reference.taxonomy,
        catalog=reference.catalog_version("v5"),
        rate_card=reference.rate_card(rates),
        parameters=reference.parameter_set(params),
    )
    for key, value in (
        ("hosting_provider", "aws"),
        ("om_years", 3),
        ("cert_in_audit", True),
        ("hypercare_weeks", 0),
    ):
        inp = answer(inp, key, value)
    return inp


@pytest.fixture
def v25(golden: Callable[[str], EstimateInput], reference: ReferenceData) -> EstimateInput:
    return project(golden, reference)


def lines(inp: EstimateInput, bucket: str, year: int | None = None) -> list[CostLineOut]:
    return [
        ln
        for ln in calculate(inp).lines
        if ln.bucket == bucket and (year is None or ln.year == year)
    ]


def step(line: CostLineOut, label: str) -> Decimal:
    return next(s.value for s in line.trace.steps if s.label.startswith(label))


def test_new_formulas_are_registered() -> None:
    assert {"hosting.bundle.v1", "maintenance.upkeep.v1"} <= FORMULAS.keys()


def test_hosting_is_one_line_a_year(v25: EstimateInput) -> None:
    hosting = lines(v25, "run.hosting")
    assert [ln.year for ln in hosting] == [1, 2, 3]
    assert {ln.formula_id for ln in hosting} == {"hosting.bundle.v1"}
    assert not lines(v25, "run.backups") and not lines(v25, "run.dr")
    assert hosting[0].high_paise > hosting[0].likely_paise > hosting[0].low_paise > 0


def test_hosting_stays_itemised_without_the_v10_rates_or_before_v25(
    golden: Callable[[str], EstimateInput], reference: ReferenceData
) -> None:
    for params, rates in (("v25", "v9"), ("v24", "v10")):
        inp = project(golden, reference, params, rates)
        formulas = {ln.formula_id for ln in lines(inp, "run.hosting")}
        assert "hosting.bundle.v1" not in formulas and len(formulas) > 1


def test_more_users_online_cost_more(v25: EstimateInput) -> None:
    low = lines(v25, "run.hosting", 1)[0].likely_paise
    high = lines(answer(v25, "peak_concurrent_users", 3000), "run.hosting", 1)[0].likely_paise
    assert high > low


def test_upkeep_is_one_line_a_year(v25: EstimateInput) -> None:
    upkeep = lines(v25, "run.patching_bugfix")
    assert [ln.year for ln in upkeep] == [1, 2, 3]
    assert {ln.formula_id for ln in upkeep} == {"maintenance.upkeep.v1"}
    assert not lines(v25, "run.change_requests")


def test_onsite_developers_do_the_upkeep(v25: EstimateInput) -> None:
    """A full-time onsite developer does more than this small project's upkeep: no upkeep line,
    the developer's own line stays."""
    dev = {"role": "role.developer", "count": 1, "covers": "upkeep", "name": "onsite developer"}
    with_dev = answer(v25, "onsite_resources", [dev])
    assert not lines(with_dev, "run.patching_bugfix")
    assert len(lines(with_dev, "run.onsite_resources")) == 3


def test_upkeep_beyond_a_few_staff_days(v25: EstimateInput) -> None:
    """Staff limited to 5 days each (year 1 only): year 1's upkeep is priced beyond those days."""
    dev = {"role": "role.developer", "count": 2, "days": 5, "covers": "upkeep"}
    year1 = lines(answer(v25, "onsite_resources", [dev]), "run.patching_bugfix", 1)[0]
    assert step(year1, "upkeep beyond them") == step(year1, "upkeep person-days") - 10
    year2 = lines(answer(v25, "onsite_resources", [dev]), "run.patching_bugfix", 2)[0]
    assert step(year2, "upkeep beyond them") == step(year2, "upkeep person-days")


def test_other_onsite_staff_leave_the_upkeep(v25: EstimateInput) -> None:
    desk = {"role": "role.developer", "count": 1, "name": "helpdesk operator"}
    before = lines(v25, "run.patching_bugfix", 2)[0].likely_paise
    after = lines(answer(v25, "onsite_resources", [desk]), "run.patching_bugfix", 2)[0]
    assert after.likely_paise == before


def test_an_onsite_pm_is_the_om_project_manager(v25: EstimateInput) -> None:
    def om_pm(inp: EstimateInput) -> int:
        return sum(
            ln.likely_paise
            for ln in lines(inp, "programme.project_management", 2)
            if ln.formula_id.startswith("programme.om_pm")
        )

    pm = {"role": "role.project_manager", "count": 1, "covers": "management"}
    assert om_pm(v25) > 0
    assert om_pm(answer(v25, "onsite_resources", [pm])) == 0


def test_annual_audit_starts_in_support_year_two(
    golden: Callable[[str], EstimateInput], reference: ReferenceData, v25: EstimateInput
) -> None:
    """The go-live audit is year 1's: 3 support years have audits in years 2 and 3 (v24: 1-3)."""
    assert [ln.year for ln in lines(v25, "run.annual_audit")] == [2, 3]
    old = project(golden, reference, "v24")
    assert [ln.year for ln in lines(old, "run.annual_audit")] == [1, 2, 3]


def test_hypercare_weeks_are_not_priced_again_in_year_one(v25: EstimateInput) -> None:
    care = answer(v25, "hypercare_weeks", 4)
    year1 = lines(care, "run.patching_bugfix", 1)[0]
    assert step(year1, "share of year 1 after hypercare") == D(48) / D(52)
    assert lines(care, "run.patching_bugfix", 1)[0].likely_paise < (
        lines(v25, "run.patching_bugfix", 1)[0].likely_paise
    )
    year2 = lines(care, "run.patching_bugfix", 2)[0]
    assert not any(s.label.startswith("share of year 1") for s in year2.trace.steps)

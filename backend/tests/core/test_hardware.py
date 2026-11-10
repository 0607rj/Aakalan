"""The hardware list for own servers (parameter sets v35+, formula hardware_list.v1,
OPEN_QUESTIONS 231): shown only when wanted, sized from the load and uptime (not the features),
the same every time, and a list only: the price does not move."""

from datetime import date
from typing import Any

from app.core.config import get_settings
from app.services.calibration.backtest import reference_for
from app.services.engine.core import calculate
from app.services.engine.formulas import FORMULAS
from app.services.engine.inputs import EstimateInput
from app.services.hosting.hardware import HardwareList, hardware_list
from app.services.quick.config import quick_config
from app.services.quick.service import QuickRequest, plan_quick, plan_to_input
from app.services.seeding.reference import load_reference

CFG = quick_config()
DATA = load_reference(get_settings().seeds_dir)


def inputs(features: list[str], version: str = "v35", **choices: Any) -> EstimateInput:
    req = QuickRequest(name="hardware", features=features, choices=choices)
    ref = {
        **reference_for(DATA, "india"),
        "parameters": DATA.parameter_set(version),
        "clarity": CFG.requirement_clarity,
    }
    return plan_to_input(
        plan_quick(CFG, req, None, "test"), req.name, ref, date(2026, 11, 10), 7, 100
    )


def listed(features: list[str], **choices: Any) -> HardwareList:
    hw = hardware_list(inputs(features, **choices))
    assert hw is not None
    return hw


def count(hw: HardwareList, key: str, site: str = "main") -> int:
    return sum(i.quantity for i in hw.items if i.key == key and i.site == site)


def test_only_when_wanted() -> None:
    assert hardware_list(inputs(["bookings"])) is None  # cloud: nothing to buy
    assert hardware_list(inputs(["bookings"], "v34", hosting="on_prem")) is None  # older set
    assert listed(["bookings"], hosting="on_prem").who_buys == "in_price"
    hw = listed(["bookings"], hosting="existing", hardware_list="client_buys")
    assert hw.who_buys == "client_buys" and hw.client_costs == []
    # on a cloud nobody buys hardware: the question is hidden and an answer dropped (232)
    assert hardware_list(inputs(["bookings"], hardware_list="client_buys")) is None


def test_two_of_each_where_the_uptime_needs_it() -> None:
    hw = listed(["bookings"], hosting="on_prem")  # 99.5%: two of each on own servers
    assert count(hw, "app_server") == 2 and count(hw, "db_server") == 2
    assert count(hw, "firewall") == 2 and count(hw, "load_balancer") == 2
    assert count(hw, "os") == count(hw, "antivirus") == 4
    assert count(hw, "rack") == 1 and count(hw, "storage") == 1


def test_a_standby_site_gets_its_own_copy() -> None:
    hw = listed(["bookings"], hosting="on_prem", disaster_site="yes")
    assert count(hw, "app_server", "standby") >= 1 and count(hw, "firewall", "standby") == 1
    assert not any(i.site == "standby" for i in listed(["bookings"], hosting="on_prem").items)


def test_load_sets_the_size_not_the_features() -> None:
    few = listed(["bookings"], hosting="on_prem")
    many = listed(["bookings", "payments", "dashboards", "documents", "billing"], hosting="on_prem")
    assert [(i.key, i.quantity, i.spec) for i in few.items] == [
        (i.key, i.quantity, i.spec) for i in many.items
    ]
    big = listed(["bookings"], hosting="on_prem", scale="up_to_10l")
    assert count(big, "app_server") > count(few, "app_server")


def test_open_source_by_default_no_database_licence() -> None:
    hw = listed(["bookings"], hosting="on_prem")
    assert count(hw, "database_licence") == 0
    assert all("no licence fee" in i.spec for i in hw.items if i.key == "os")


def test_the_list_is_the_same_every_time_and_moves_no_price() -> None:
    inp = inputs(["bookings"], hosting="existing", hardware_list="client_buys")
    assert hardware_list(inp) == hardware_list(inp)
    plain = calculate(inputs(["bookings"], hosting="existing"))
    with_list = calculate(inp)
    assert plain.totals is not None and with_list.totals is not None
    assert with_list.totals.likely_paise == plain.totals.likely_paise
    assert "hardware_list.v1" in FORMULAS


def test_own_building_pays_no_rack_rent() -> None:
    """v36+ (OPEN_QUESTIONS 232): servers in the client's own building pay no data-centre rack
    rent; the hardware AMC stays; power, cooling and the room are listed as the client's own
    costs. v35 kept the rent, and an estimate on it keeps its price."""
    own = calculate(inputs(["bookings"], "v36", hosting="on_prem", support_years=2))
    old = calculate(inputs(["bookings"], "v35", hosting="on_prem", support_years=2))
    keys = {ln.formula_id for ln in own.lines}
    assert "hosting.onprem_colocation.v1" not in keys and "hosting.onprem_amc.v1" in keys
    assert "hosting.onprem_colocation.v1" in {ln.formula_id for ln in old.lines}
    assert own.totals is not None and old.totals is not None
    assert own.totals.likely_paise < old.totals.likely_paise
    hw = hardware_list(inputs(["bookings"], "v36", hosting="on_prem"))
    assert hw is not None and any("Power" in c for c in hw.client_costs)


def test_own_servers_are_priced_from_the_list() -> None:
    """v37 (OPEN_QUESTIONS 233): the buying line is the list's one-time items × rate card
    prices; licences are yearly lines; every price is named in the trace."""
    inp = inputs(["bookings"], "v37", hosting="on_prem", support_years=3)
    hw = hardware_list(inp)
    assert hw is not None and hw.once_paise and hw.yearly_paise is not None
    lines = calculate(inp).lines
    capex = [ln for ln in lines if ln.formula_id == "golive.onprem_capex.v2"]
    assert len(capex) == 1 and capex[0].likely_paise == hw.once_paise
    assert "golive.onprem_capex.v1" not in {ln.formula_id for ln in lines}  # no guessed price
    subs = [ln for ln in lines if ln.formula_id == "hosting.onprem_subscriptions.v1"]
    assert len(subs) == 3  # one a year
    named = {r.key for r in capex[0].trace.rate_items}
    assert {"onprem.hw.firewall", "onprem.hw.rack_42u", "onprem.hw.ups_5kva"} <= named
    for formula in ("golive.onprem_capex.v2", "hosting.onprem_subscriptions.v1"):
        assert formula in FORMULAS


def test_small_sites_share_servers_large_ones_do_not() -> None:
    """The application and database share each server while one 16-core server holds both;
    a server is priced by its size."""
    small = hardware_list(inputs(["bookings"], "v37", hosting="on_prem"))
    assert small is not None
    shared = [i for i in small.items if i.key == "single_server"]
    assert count(small, "app_server") == 0 and shared and shared[0].quantity == 2
    assert shared[0].rate_keys == ["onprem.hw.server_16c"]
    big = hardware_list(inputs(["bookings"], "v37", hosting="on_prem", scale="up_to_1l"))
    assert big is not None and count(big, "single_server") == 0
    assert count(big, "app_server") > 0 and count(big, "db_server") > 0


def test_old_sets_keep_the_old_price() -> None:
    """Before v37 own servers keep the per-server price (estimates never change)."""
    lines = calculate(inputs(["bookings"], "v36", hosting="on_prem")).lines
    formulas = {ln.formula_id for ln in lines}
    assert "golive.onprem_capex.v1" in formulas and "golive.onprem_capex.v2" not in formulas

"""Standard blocks between two project sizes (OPEN_QUESTIONS 183): near a tier edge they are
priced partly at the next size, so one feature more never resizes every block at once."""

from decimal import Decimal

import pytest

from app.services.engine.components import mixed_base_pd
from app.services.engine.inputs import ComponentInstanceIn
from app.services.engine.reference import CatalogComponent, Size
from app.services.quick.config import quick_config
from app.services.quick.service import QuickRequest, plan_quick


def test_neighbour_share_moves_in_a_line_across_an_edge() -> None:
    sizing = quick_config().sizing
    assert sizing.tier_blend_share == Decimal("0.25")

    def near(points: int) -> tuple[str, str | None, Decimal]:
        tier, share = sizing.neighbour(points)
        return sizing.tier(points).project_size, tier.project_size if tier else None, share

    # the edge at 20 points (medium | medium_large): 15 to 25 points
    assert near(14) == ("medium", None, Decimal(0))
    assert near(16) == ("medium", "medium_large", Decimal("0.1"))
    assert near(20) == ("medium", "medium_large", Decimal("0.5"))
    assert near(21) == ("medium_large", "medium", Decimal("0.4"))
    assert near(25) == ("medium_large", None, Decimal(0))


def test_blocks_of_the_next_size_come_in_part() -> None:
    cfg = quick_config()
    # bookings and payments: 4 points, half way across the edge at 4 (small | small_medium)
    plan = plan_quick(cfg, QuickRequest(name="x", features=["bookings", "payments"]), {}, "")
    mixes = {c.key: c.size_mix for c in plan.components}
    assert plan.size_points == 4 and plan.project_size == "small"
    assert mixes["ui_ux_design"] is None  # S in both sizes: priced in full
    assert mixes["discovery_requirement_study"] == {Size.S: Decimal("0.5")}  # small_medium's
    assert mixes["integration_payment_gateway"] is None  # a feature's own block: in full


def test_a_block_priced_between_sizes(catalog_component: CatalogComponent) -> None:
    ci = ComponentInstanceIn(
        id="C1",
        catalog_key=catalog_component.key,
        size=Size.M,
        size_mix={Size.S: Decimal("0.3"), Size.M: Decimal("0.7")},
    )
    base = catalog_component.base_effort_pd
    assert mixed_base_pd(ci, catalog_component) == base[Size.S] * Decimal("0.3") + base[
        Size.M
    ] * Decimal("0.7")
    with pytest.raises(ValueError, match="size_mix"):
        ComponentInstanceIn(
            id="C2",
            catalog_key="x",
            size=Size.M,
            size_mix={Size.S: Decimal("0.6"), Size.M: Decimal("0.6")},
        )


@pytest.fixture
def catalog_component() -> CatalogComponent:
    from app.core.config import get_settings
    from app.services.seeding.reference import load_reference

    catalog = load_reference(get_settings().seeds_dir).catalog_version("v7")
    return catalog.get("ui_ux_design")


def test_lean_delivery_and_launch_defaults_move_across_an_edge() -> None:
    """Near the small-to-medium | medium edge the lean share passes to the engine
    (size_blend), and the launch defaults sit between the two sizes' numbers (OPEN_QUESTIONS
    184)."""
    cfg = quick_config()
    reports: dict[str, str | int] = {"reporting": "yes"}  # formal reports: lean by size only
    fs = ["online_forms", "approval_workflow", "documents", "dashboards", "ai_chatbot"]
    plan = plan_quick(cfg, QuickRequest(name="x", features=fs, choices=reports), {}, "")
    assert (plan.size_points, plan.project_size) == (10, "small_medium")
    assert plan.answers["size_blend"][0] == {"size": "medium", "share": "0.5"}
    # the medium | medium-large edge: 2 hypercare weeks and 2 training sessions below it, 4
    # and 4 above; the first feature list that falls in its window
    keys = [f.key for f in cfg.features if not f.hidden]
    plans = (
        plan_quick(cfg, QuickRequest(name="x", features=keys[:n]), {}, "") for n in range(1, 30)
    )
    near = next(p for p in plans if 15 < p.size_points < 25 and p.size_points != 20)
    blend = near.answers["size_blend"][0]
    other = "medium_large" if near.project_size == "medium" else "medium"
    assert blend["size"] == other
    upper = Decimal(blend["share"]) if other == "medium_large" else 1 - Decimal(blend["share"])
    assert Decimal(near.answers["hypercare_weeks"][0]) == 2 + 2 * upper
    assert Decimal(near.answers["training_sessions"][0]) == 2 + 2 * upper

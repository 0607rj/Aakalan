"""Researched blocks: page checks, hours rule, catalog matching, AI analysis, safe fetching."""

from decimal import Decimal

import pytest

from app.core.config import get_settings
from app.services.engine.reference import Size
from app.services.quick.config import quick_config
from app.services.research.fetch import FetchError, fetch_text, html_text
from app.services.research.service import (
    FoundSource,
    Part,
    check_source,
    composed_effort,
    derive_effort,
    find_block,
    slug,
    standard_blocks,
    valid_parts,
)
from app.services.seeding.reference import load_reference


def source(**kw: object) -> FoundSource:
    base = {
        "url": "https://example.com/guide",
        "label": "Push notifications",
        "quote": "Push notifications: 40-80 hours",
        "low": Decimal(40),
        "high": Decimal(80),
    }
    return FoundSource.model_validate({**base, **kw})


def test_figure_must_be_on_the_page() -> None:
    page = "<p>Feature costs</p><table><tr><td>Push notifications</td><td>40–80 hours</td></tr>"
    text = html_text(page)
    assert check_source(source(), text, 300) == ""  # quote differs (en dash), label is near
    assert "not on the page" in check_source(source(high=Decimal(90)), text, 300)
    far = "Push notifications are useful. " + "x " * 400 + "40-80 hours"
    assert "not next to" in check_source(source(quote="other words"), far, 100)
    assert check_source(source(), "Push   notifications: 40-80 Hours", 300) == ""


def test_hours_rule() -> None:
    effort = derive_effort([Decimal(40), Decimal(80), Decimal(120)], Decimal("0.9"), 8)
    assert effort == {Size.S: Decimal("4.5"), Size.M: Decimal("9.0"), Size.L: Decimal("13.5")}
    assert derive_effort([Decimal(1)], Decimal("0.9"), 8)[Size.S] == Decimal("0.1")


def test_catalog_match_skips_generic_blocks() -> None:
    catalog = load_reference(get_settings().seeds_dir).catalog
    found = find_block("Push notifications", catalog.components, Decimal("0.6"))
    assert found is not None and found.key == "push_notifications"
    assert find_block("Custom AI feature", catalog.components, Decimal("0.6")) is None
    assert find_block("Vehicle tracking with GIS map", catalog.components, Decimal("0.6")) is None
    assert slug("Fleet Geofencing alerts") == "researched_alert_fleet_geofencing"


def test_analysis_uses_only_catalog_hours() -> None:
    cfg = quick_config()
    catalog = load_reference(get_settings().seeds_dir).catalog
    standard = standard_blocks(cfg)
    parts = [
        Part(block="push_notifications", level="standard"),
        Part(block="push_notifications", level="advanced"),  # duplicate: dropped
        Part(block="not_a_block", level="basic"),  # unknown: dropped
        Part(block="custom_module", level="basic"),  # generic: dropped
        Part(block="ui_ux_design", level="basic"),  # in every project: dropped
    ]
    kept = valid_parts(parts, catalog, standard)
    assert [p.block for p in kept] == ["push_notifications"]
    sizes: dict[str, Size] = {k: v.component_size for k, v in cfg.sizing.levels.items()}
    effort = composed_effort(kept, catalog, sizes)
    push = catalog.get("push_notifications").base_effort_pd
    assert effort[Size.M] == push[sizes["standard"]]
    assert effort[Size.S] <= effort[Size.M] <= effort[Size.L]


@pytest.mark.parametrize(
    "url",
    [
        "file:///etc/passwd",
        "http://127.0.0.1/",
        "http://localhost/",
        "http://10.0.0.5/x",
        "http://169.254.169.254/latest/meta-data",
        "ftp://example.com/",
    ],
)
def test_fetch_refuses_non_public_addresses(url: str) -> None:
    with pytest.raises(FetchError):
        fetch_text(url, 5, 1000)

"""Catalog v8 (OPEN_QUESTIONS 213): every v7 component and number unchanged, and blocks for the
industry modules, each citing published hours with a link; the industry lists price their
modules from them."""

from app.services.engine.reference import BaselineEra, EraBasis, Size
from app.services.quick.config import quick_config
from app.services.quick.service import CustomFeature, QuickRequest, plan_quick
from app.services.seeding.reference import ReferenceData


def test_v8_keeps_every_v7_component_and_number(reference: ReferenceData) -> None:
    v7, v8 = reference.catalog_version("v7"), reference.catalog_version("v8")
    assert v8.components[: len(v7.components)] == v7.components
    assert set(v7.sections) <= set(v8.sections)


def test_new_v8_blocks_cite_published_hours(reference: ReferenceData) -> None:
    v7, v8 = reference.catalog_version("v7"), reference.catalog_version("v8")
    new = v8.components[len(v7.components) :]
    assert len(new) == 15
    for c in new:
        assert c.section in v8.sections and c.evidence, c.key
        assert any(e.source_type == "vendor_estimate" for e in c.evidence), c.key
        for e in c.evidence:
            if e.source_type == "vendor_estimate":
                assert e.url and e.url.startswith("https://"), e.id
            # AI-assisted only where the source says so: then no AI saving is taken off
            if e.era is BaselineEra.AI_ASSISTED:
                assert e.era_basis is EraBasis.EXPLICIT_STATEMENT and e.ai_workflow, e.id


def test_every_industry_block_is_in_the_newest_catalog(reference: ReferenceData) -> None:
    cfg = quick_config()
    keys = {c.key for c in reference.catalog.components}
    assert cfg.industries is not None
    blocks = [i.block for ind in cfg.industries.items for i in ind.features if i.block]
    assert len(blocks) >= 18 and set(blocks) <= keys
    for ind in cfg.industries.items:
        for item in ind.features:
            assert not (item.block and item.feature), (ind.key, item.block)


def test_a_module_is_priced_from_its_own_block() -> None:
    cfg = quick_config()
    attendance = CustomFeature(
        name="Daily attendance", category="module", size=Size.M, catalog_key="attendance_tracking"
    )
    generic = CustomFeature(name="Daily attendance", category="module", size=Size.M)
    with_block = plan_quick(
        cfg, QuickRequest(name="School", custom_features=[attendance]), None, ""
    )
    without = plan_quick(cfg, QuickRequest(name="School", custom_features=[generic]), None, "")
    assert "attendance_tracking" in {c.key for c in with_block.components}
    assert "attendance_tracking" not in {c.key for c in without.components}
    assert "custom_module" in {c.key for c in without.components}

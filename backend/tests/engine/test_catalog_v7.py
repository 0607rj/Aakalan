"""Catalog v7: every v6 component and number unchanged, a tech-stack section for every
component, and new blocks that each cite their sources (and a link for every vendor figure)."""

import pytest
from pydantic import ValidationError

from app.services.engine.reference import BaselineEra, Catalog
from app.services.quick.config import quick_config
from app.services.quick.service import QuickRequest, plan_quick
from app.services.seeding.reference import ReferenceData


def test_v7_keeps_every_v6_component_and_number(reference: ReferenceData) -> None:
    v6, v7 = reference.catalog_version("v6"), reference.catalog_version("v7")
    old = v7.components[: len(v6.components)]
    assert [c.key for c in old] == [c.key for c in v6.components]
    for new, before in zip(old, v6.components, strict=True):
        assert new.model_copy(update={"section": None}) == before


def test_every_v7_component_is_in_a_section(reference: ReferenceData) -> None:
    v7 = reference.catalog_version("v7")
    assert {c.section for c in v7.components} == set(v7.sections)
    data = v7.model_dump()
    data["components"][0]["section"] = "nowhere"
    with pytest.raises(ValidationError, match="not a catalog section"):
        Catalog.model_validate(data)


def test_new_v7_blocks_cite_their_sources(reference: ReferenceData) -> None:
    v6, v7 = reference.catalog_version("v6"), reference.catalog_version("v7")
    new = v7.components[len(v6.components) :]
    assert len(new) == 27
    for c in new:
        assert c.evidence, c.key
        assert c.source_era is BaselineEra.UNKNOWN  # no source states AI use: no AI saving
        assert c.confidence in {"low", "low_medium"}
        for e in c.evidence:
            if e.source_type == "vendor_estimate":
                assert e.url and e.url.startswith("https://"), e.id


def test_quick_features_and_scope_use_v7_blocks(reference: ReferenceData) -> None:
    cfg = quick_config()
    keys = {c.key for c in reference.catalog_version("v7").components}
    for f in cfg.features:
        assert set(f.components) <= keys, f.key
    for group in cfg.scope:
        for item in group.items:
            assert set(item.adds) <= keys, item.key


def test_a_new_feature_is_priced_from_its_block() -> None:
    cfg = quick_config()
    req = QuickRequest(
        name="Shop", features=["online_store", "marketplace"], scope=["store_coupons"]
    )
    plan = plan_quick(cfg, req, None, "")
    keys = {c.key for c in plan.components}
    assert {"ecommerce_storefront", "marketplace_multivendor", "coupons_promotions"} <= keys

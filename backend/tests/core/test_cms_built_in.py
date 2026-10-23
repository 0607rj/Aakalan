"""What a CMS already has is set up, not built (cms_built_in, OPEN_QUESTIONS 154)."""

from app.services.engine.reference import Size
from app.services.quick.config import quick_config
from app.services.quick.service import CustomFeature, QuickPlan, QuickRequest, plan_quick

CFG = quick_config()
RULE = CFG.cms_built_in


def plan(build_type: str) -> QuickPlan:
    req = QuickRequest(
        name="x",
        features=["public_website", "payments"],
        feature_levels={"public_website": "advanced", "payments": "advanced"},
        feature_units={"public_website": 3},
        custom_features=[
            CustomFeature(name="CMS editor and publishing tools", category="module", size=Size.L),
            CustomFeature(name="Loan calculators", category="module", size=Size.L),
        ],
        choices={"build_type": build_type},
    )
    return plan_quick(CFG, req, None, "test")


def test_on_a_cms_its_own_features_are_set_up_not_built() -> None:
    assert RULE is not None and "cms" in RULE.build_types
    cms, custom = plan("cms"), plan("custom")
    assert cms.levels["public_website"] == RULE.level  # capped, one module
    assert custom.levels["public_website"] == "advanced"
    assert cms.levels["payments"] == "advanced"  # a CMS does not ship payments
    assert cms.size_points < custom.size_points
    sizes = {c.label: c.size for c in cms.components if c.label}
    assert sizes["Loan calculators"] == "L"  # not a CMS part: unchanged
    assert sizes["CMS editor and publishing tools"] != "L"
    notes = [r.text for r in cms.requirements.values() if RULE.note in r.text]
    assert len(notes) == 2  # the website and the editor say why they cost little


def test_cms_parts_are_matched_by_whole_words() -> None:
    assert RULE is not None
    assert RULE.is_cms_part("SEO controls") and RULE.is_cms_part("Page templates")
    assert not RULE.is_cms_part("Seoul office directory")

"""The story-size check (services/quick/size_check.py, OPEN_QUESTIONS 163)."""

from decimal import Decimal

from app.services.quick.config import SizeCheck, quick_config
from app.services.quick.size_check import SizedFeature, function_points, size_check


def rules() -> SizeCheck:
    found = quick_config().size_check
    assert found is not None
    return found


def test_function_points_per_story() -> None:
    # 10 stories × (4.6 + 0.3 × 7.0) = 67
    assert function_points(rules(), 10) == Decimal("67.0")


def test_inside_the_story_size_agrees() -> None:
    # 10 stories = 67 FP: 315 / 657 / 1233 hours
    out = size_check(rules(), [SizedFeature("Approvals", "Standard", 10, Decimal(600))], [])
    assert out.available
    assert (out.story_hours_low, out.story_hours, out.story_hours_high) == (315, 657, 1233)
    assert out.position == "inside"
    assert out.methods_agree is True
    assert out.features == []


def test_a_feature_far_below_is_listed() -> None:
    sized = [
        SizedFeature("Approvals", "Standard", 10, Decimal(700)),
        SizedFeature("Payments", "Basic", 6, Decimal(20)),
        SizedFeature("Tiny", None, 2, Decimal(1)),  # under min_stories: not judged alone
    ]
    out = size_check(rules(), sized, ["Mobile app"])
    assert [f.label for f in out.features] == ["Payments"]
    assert out.features[0].position == "below"
    assert out.unsized == ["Mobile app"]


def test_a_reused_build_gives_no_verdict() -> None:
    sized = [SizedFeature("Approvals", "Standard", 10, Decimal(100))]
    out = size_check(rules(), sized, [], reused="Set up a ready-made product")
    assert out.position == "below"
    assert out.methods_agree is None
    assert out.message.startswith("Set up a ready-made product")


def test_no_stories_no_check() -> None:
    out = size_check(rules(), [SizedFeature("Approvals", None, 0, Decimal(100))], ["Approvals"])
    assert not out.available


def test_hours_with_ai_tools_are_shown_not_compared() -> None:
    sized = [SizedFeature("Approvals", "Standard", 10, Decimal(600), Decimal(450))]
    out = size_check(rules(), sized, [])
    assert (out.our_hours, out.our_hours_with_ai) == (600, 450)
    assert out.features == [] and out.position == "inside"  # judged on 600, not 450


def test_headline_is_plain_and_names_the_features() -> None:
    sized = [
        SizedFeature("Approvals", "Standard", 10, Decimal(700)),
        SizedFeature("Payments", "Basic", 6, Decimal(20)),
    ]
    out = size_check(rules(), sized, [])
    assert out.headline == (
        "Our build size matches a standard industry method. "
        "1 feature may be priced low: Payments. Check it."
    )
    assert "function point" not in out.headline.lower()

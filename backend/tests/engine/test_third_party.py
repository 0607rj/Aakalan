"""Third-party costs (parameter sets v5 / us-v4): build-phase tools, usage-billed services,
AI features, translation and the client-paid list."""

from collections.abc import Callable
from decimal import Decimal

import pytest

from app.services.engine.core import calculate
from app.services.engine.formulas import FORMULAS
from app.services.engine.inputs import EstimateInput
from app.services.engine.money import to_paise
from app.services.engine.outputs import CostLineOut, EstimateResult
from app.services.seeding.reference import ReferenceData
from tests.engine.conftest import answer, tweak

D = Decimal
INDIA = ("v3", "v5")
US = ("us-v2", "us-v4")


@pytest.fixture
def current(
    golden: Callable[[str], EstimateInput], reference: ReferenceData
) -> Callable[..., EstimateInput]:
    """The medium golden project priced on the current reference data, with extra components
    and usage fees in the quote (unless the test says otherwise)."""

    def make(*extra: str, region: tuple[str, str] = INDIA, **answers: object) -> EstimateInput:
        base = golden("medium")
        template = base.components[0].model_dump()
        components = [c.model_dump() for c in base.components] + [
            {**template, "id": f"extra-{key}", "catalog_key": key, "requirement_ids": []}
            for key in extra
        ]
        inp = tweak(
            base,
            components=components,
            taxonomy=reference.taxonomy,
            catalog=reference.catalog,
            rate_card=reference.rate_card(region[0]),
            parameters=reference.parameter_set(region[1]),
        )
        for key, value in {"usage_fees_in_scope": True, **answers}.items():
            inp = answer(inp, key, value)
        return inp

    return make


def keys(lines: list[CostLineOut]) -> set[str]:
    return {ln.line_key for ln in lines}


def line(result: EstimateResult, key: str) -> CostLineOut:
    return next(ln for ln in result.lines if ln.line_key == key)


def test_older_parameter_sets_add_nothing(golden: Callable[[str], EstimateInput]) -> None:
    result = calculate(golden("medium"))
    assert not result.client_paid and not result.client_paid_notes
    assert not any(ln.bucket in ("build.tools", "run.third_party_services") for ln in result.lines)


def test_sms_hand_computed(current: Callable[..., EstimateInput]) -> None:
    inp = current("notifications")
    result = calculate(inp)
    p, card = inp.parameters, {i.key: i for i in inp.rate_card.items}
    users = next(a.value for a in inp.answers if a.key == "users_total")
    sms = next(s for s in p.third_party.services if s.key == "sms")  # type: ignore[union-attr]
    esc = next((a.value for a in inp.answers if a.key == "escalation_prices"), None)
    rate_esc = D(str(esc)) if esc is not None else p.escalation.prices
    expected = (
        D(users)  # type: ignore[arg-type]
        * p.hosting.monthly_active_share
        * sms.units_per_active_user_month
        * (p.calendar.pd_per_year / p.calendar.pd_per_month)
        * card["service.sms.message"].amount
        * (1 + rate_esc)
    )
    assert line(result, "run.third_party_services/sms/y1").likely_paise == to_paise(expected)


def test_ekyc_charged_to_private_buyers_only(current: Callable[..., EstimateInput]) -> None:
    key = "run.third_party_services/aadhaar_ekyc/y1"
    private = calculate(current("integration_aadhaar_ekyc", buyer_segment="private"))
    government = calculate(current("integration_aadhaar_ekyc", buyer_segment="government"))
    us = calculate(current("integration_aadhaar_ekyc", region=US, buyer_segment="private"))
    assert key in keys(private.lines)
    assert key not in keys(government.lines) and key not in keys(us.lines)
    later = line(private, "run.third_party_services/aadhaar_ekyc/y2").likely_paise
    assert later < line(private, key).likely_paise  # only new users after year 1


def test_ai_coding_seats_only_with_ai_tools(current: Callable[..., EstimateInput]) -> None:
    with_ai = calculate(current(team_ai_maturity="medium"))
    by_hand = calculate(current(team_ai_maturity="none"))
    assert "build.tools/ai_coding" in keys(with_ai.lines)
    assert "build.tools/ai_coding" not in keys(by_hand.lines)
    assert "build.tools/dev_suite" in keys(by_hand.lines)
    # seats follow build effort: more effort by hand -> more dev-suite seat-months
    suite = "build.tools/dev_suite"
    assert line(by_hand, suite).likely_paise > line(with_ai, suite).likely_paise


def test_client_hosting_moves_hosting_to_client_paid(
    current: Callable[..., EstimateInput],
) -> None:
    ours = calculate(current(hosting_in_scope=True, users_total=50000))
    theirs = calculate(current(hosting_in_scope=False, users_total=50000))
    assert "run.hosting/compute/y1" in keys(ours.lines)
    assert "run.third_party_services/waf_base/y1" in keys(ours.lines)
    assert not any(ln.bucket == "run.hosting" for ln in theirs.lines)
    assert {"run.hosting/compute/y1", "run.third_party_services/waf_base/y1"} <= keys(
        theirs.client_paid
    )
    assert not ours.client_paid
    assert theirs.totals and ours.totals
    assert theirs.totals.likely_paise < ours.totals.likely_paise


def test_usage_fees_paid_by_client_by_default(
    current: Callable[..., EstimateInput], reference: ReferenceData
) -> None:
    for version in ("v5", "us-v4"):
        assert reference.parameter_set(version).defaults.values["usage_fees_in_scope"] is False
    result = calculate(current("notifications", "custom_ai_feature", usage_fees_in_scope=False))
    quoted = keys(result.lines)
    assert "run.third_party_services/sms/y1" not in quoted  # the firewall stays with hosting
    assert "run.ai_runtime/ai_features/y1" in quoted  # AI running cost stays in the price
    assert "run.third_party_services/sms/y1" in keys(result.client_paid)


def test_mobile_app_store_fees(current: Callable[..., EstimateInput]) -> None:
    result = calculate(current("custom_mobile_app"))
    found = keys(result.lines)
    assert "run.third_party_services/apple_developer/y2" in found
    assert "run.third_party_services/google_play/y1" in found
    assert "run.third_party_services/google_play/y2" not in found  # one-off


def test_translation_only_for_extra_languages(current: Callable[..., EstimateInput]) -> None:
    one = calculate(current(languages=1))
    two = calculate(current(languages=2))
    three = calculate(current(languages=3))
    assert "build.content_translation/content" not in keys(one.lines)
    k = "build.content_translation/content"
    assert line(three, k).likely_paise == 2 * line(two, k).likely_paise


def test_payment_fee_note(current: Callable[..., EstimateInput]) -> None:
    inp = current("integration_payment_gateway")
    india = calculate(inp)
    us = calculate(current("integration_payment_gateway", region=US))
    payment = ("integration_payment_gateway", "ecommerce_storefront")
    kept = [c.model_dump() for c in inp.components if c.catalog_key not in payment]
    without = calculate(tweak(inp, components=kept))
    assert "2%" in india.client_paid_notes[0].text
    assert "2.9% + USD 0.30" in us.client_paid_notes[0].text
    assert india.client_paid_notes[0].rates[0].source_url
    assert not any(n.key == "payment_gateway" for n in without.client_paid_notes)


def test_new_lines_carry_full_trace(current: Callable[..., EstimateInput]) -> None:
    inp = current(
        "notifications",
        "custom_ai_feature",
        "maps_location",
        "custom_mobile_app",
        "integration_aadhaar_ekyc",
        languages=2,
        users_total=50000,
        buyer_segment="private",
    )
    result = calculate(inp)
    new = [
        ln
        for ln in result.lines
        if ln.bucket in ("build.tools", "build.content_translation", "run.third_party_services")
        or "ai_features" in ln.line_key
    ]
    assert len({ln.line_key.split("/")[1] for ln in new}) >= 10
    for ln in new:
        assert ln.formula_id in FORMULAS and ln.trace.formula == FORMULAS[ln.formula_id]
        assert ln.trace.rate_items and ln.trace.steps, ln.line_key
        assert all(r.rate_card_version == "v3" for r in ln.trace.rate_items)
        assert 0 < ln.low_paise <= ln.likely_paise <= ln.high_paise, ln.line_key


def test_simple_ai_model_is_cheaper(
    golden: Callable[[str], EstimateInput], reference: ReferenceData
) -> None:
    base = tweak(
        golden("medium"),
        taxonomy=reference.taxonomy,
        catalog=reference.catalog,
        rate_card=reference.rate_card("v4"),
        parameters=reference.parameter_set("v7"),
    )
    key = "run.ai_runtime/llm_api/y1"
    advanced = line(calculate(answer(base, "ai_model_tier", "advanced")), key)
    simple = line(calculate(answer(base, "ai_model_tier", "simple")), key)
    assert simple.likely_paise * 10 < advanced.likely_paise
    assert {r.key for r in simple.trace.rate_items} >= {
        "llm_token.simple.input",
        "llm_token.simple.output",
    }
    # older parameter sets have one tier: the answer changes nothing
    old = tweak(base, rate_card=reference.rate_card("v3"), parameters=reference.parameter_set("v6"))
    assert (
        line(calculate(answer(old, "ai_model_tier", "simple")), key).likely_paise
        == line(calculate(old), key).likely_paise
    )

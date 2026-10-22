"""Scope items: effort follows what a feature really needs (catalog blocks at a level, priced by
the engine), each block counted once however many features or items ask for it."""

from collections import Counter
from datetime import date
from decimal import Decimal
from typing import Any

import pytest
from fastapi import HTTPException

from app.core.config import get_settings
from app.services.calibration.backtest import reference_for
from app.services.engine.core import calculate
from app.services.engine.outputs import EstimateResult
from app.services.quick.config import quick_config
from app.services.quick.service import QuickPlan, QuickRequest, plan_quick, plan_to_input
from app.services.seeding.reference import load_reference

CFG = quick_config()
REF = reference_for(load_reference(get_settings().seeds_dir), "india")
REF["clarity"] = CFG.requirement_clarity
SMALL = ["bookings"]  # 2 feature points: a small project (user accounts at size S)
MEDIUM = ["online_forms", "approval_workflow", "documents", "dashboards", "payments", "grievances"]


def plan(features: list[str], scope: list[str] | None = None, **kw: Any) -> QuickPlan:
    req = QuickRequest(name="x", features=features, scope=scope or [], **kw)
    return plan_quick(CFG, req, None, "test")


def price(p: QuickPlan, runs: int = 200) -> EstimateResult:
    return calculate(plan_to_input(p, "x", REF, date(2026, 10, 19), 11, runs))


def blocks(p: QuickPlan) -> Counter[str]:
    return Counter(c.key for c in p.components)


def size_of(p: QuickPlan, key: str) -> str:
    return next(c.size.value for c in p.components if c.key == key)


def effort(p: QuickPlan) -> Decimal:
    return price(p).timeline.build_effort_pd


def test_simple_sign_in_and_enterprise_sign_in_differ() -> None:
    """Same block, different scope: Google sign-in is the basic single sign-on block, the
    organisation's own SAML / Active Directory login the standard one (about 127 h; the
    catalog's sources: 80-150 h)."""
    social, sso = plan(SMALL, ["social_login"]), plan(SMALL, ["enterprise_sso"])
    assert size_of(social, "integration_sso_identity") == "S"
    assert size_of(sso, "integration_sso_identity") == "M"
    assert effort(plan(SMALL)) < effort(social) < effort(sso)
    both = plan(SMALL, ["social_login", "enterprise_sso"])  # one block, the larger level
    assert blocks(both)["integration_sso_identity"] == 1 and effort(both) == effort(sso)


def test_mfa_adds_its_increment_not_a_bigger_user_accounts_block() -> None:
    """Two-step sign-in adds the SMS / email service for the codes (about 26 h). It used to
    make the whole user-accounts block one size bigger (S 76 h -> M 252 h): a larger module,
    not MFA's own work, so it no longer does."""
    base, mfa, otp = plan(SMALL), plan(SMALL, ["two_step_sign_in"]), plan(SMALL, ["otp_codes"])
    assert size_of(mfa, "user_management_rbac") == size_of(base, "user_management_rbac") == "S"
    assert set(blocks(mfa)) - set(blocks(base)) == {"integration_sms_email_gateway"}
    assert size_of(mfa, "integration_sms_email_gateway") == "S"
    assert effort(base) < effort(mfa) == effort(otp)
    added = effort(mfa) - effort(base)
    assert added < Decimal("4") * Decimal("1.4")  # the gateway's S effort, not a size step


def test_no_scope_item_makes_a_standard_block_bigger() -> None:
    """Items may ask for a standard block only at basic, so they never step it up a size."""
    standard = {k for t in CFG.sizing.tiers for k in t.base_components}
    for group in CFG.scope:
        for item in group.items:
            assert all(lv == "basic" for k, lv in item.adds.items() if k in standard), item.key
    data = CFG.model_dump()
    data["scope"][0]["items"][0]["adds"] = {"user_management_rbac": "standard"}
    with pytest.raises(ValueError, match="may not make"):
        type(CFG).model_validate(data)


def test_scope_adds_effort_only_when_it_adds_work() -> None:
    """An audit log is its own block on a small project and a standard block of medium ones:
    asking for it there adds nothing."""
    assert effort(plan(SMALL, ["audit_log"])) > effort(plan(SMALL))
    medium = plan(MEDIUM)
    assert "audit_trail_logging" in blocks(medium)
    assert effort(plan(MEDIUM, ["audit_log", "workflow_audit", "documents_audit"])) == effort(
        medium
    )


def test_an_integration_is_not_added_twice() -> None:
    """Collecting an application fee needs a payment gateway: one more block on its own, none
    when the payments feature already brings it."""
    forms = ["online_forms"]
    fee = plan(forms, ["forms_fee"])
    assert blocks(fee)["integration_payment_gateway"] == 1
    assert effort(fee) > effort(plan(forms))
    with_payments = plan([*forms, "payments"], ["forms_fee"])
    assert blocks(with_payments)["integration_payment_gateway"] == 1
    assert effort(with_payments) == effort(plan([*forms, "payments"]))


def test_shared_blocks_are_charged_once() -> None:
    """Two-step sign-in, one-time codes and approval alerts all need the SMS / email gateway:
    it is built once."""
    features = ["approval_workflow"]
    one = plan(features, ["otp_codes"])
    many = plan(features, ["otp_codes", "two_step_sign_in", "workflow_alerts"])
    assert blocks(many)["integration_sms_email_gateway"] == 1
    assert blocks(many)["notifications"] == 1
    assert all(n == 1 for n in blocks(many).values())
    gateway = next(c for c in many.components if c.key == "integration_sms_email_gateway")
    assert len(gateway.requirements) == 3  # traced to every item that needs it
    assert effort(many) > effort(one)  # the alerts' notifications block is new; the gateway is not


def test_reports_and_alerts_reuse_the_blocks_already_there() -> None:
    """Pending-file reports need the reports block and step alerts the notifications and SMS
    blocks: nothing is added when the dashboards and notifications features bring them."""
    features = ["approval_workflow", "dashboards", "notifications"]
    base = plan(features)
    both = plan(features, ["workflow_reports", "workflow_alerts"])
    assert blocks(both) == blocks(base)
    assert effort(both) == effort(base)
    alone = plan(["approval_workflow"], ["workflow_reports", "workflow_alerts"])
    assert {"dashboard_mis_reports", "notifications", "integration_sms_email_gateway"} <= set(
        blocks(alone)
    )


def test_two_items_on_the_general_block_are_two_systems() -> None:
    """An API for other systems and an e-signature service both use the catalog's general
    integration block: two different connections, so two blocks (not merged as shared)."""
    p = plan(["documents"], ["public_api", "documents_esign"])
    general = [c for c in p.components if c.key == "custom_integration"]
    assert len(general) == 2 and {c.label for c in general} == {
        "An API or webhooks so other systems can use it",
        "Digital signatures (eSign or DSC)",
    }
    one = plan(["documents"], ["public_api"])
    assert effort(p) > effort(one) > effort(plan(["documents"]))


def test_irrelevant_changes_do_not_change_the_price() -> None:
    base = price(plan(SMALL, ["otp_codes", "booking_payment"]))
    for other in (
        plan(SMALL, ["booking_payment", "otp_codes"]),  # order
        plan(SMALL, ["otp_codes", "otp_codes", "booking_payment"]),  # repeats
        plan(SMALL, ["otp_codes", "booking_payment"], project_type="portal"),  # first screen
    ):
        result = price(other)
        assert result.totals == base.totals
        assert [ln.likely_paise for ln in result.lines] == [ln.likely_paise for ln in base.lines]


def test_same_scope_reproduces_exactly() -> None:
    p = plan(MEDIUM, ["two_step_sign_in", "workflow_reports"])
    assert price(p, 500).model_dump_json() == price(p, 500).model_dump_json()


def test_scope_is_work_not_an_ai_discount() -> None:
    """Scope adds the blocks' work; the team's AI tools are applied afterwards by the existing
    era rules (catalog v6: no saving on unknown-era data), the same with or without scope."""
    for level in ("none", "medium"):
        without = effort(plan(SMALL, choices={"ai_use": level}))
        with_sso = effort(plan(SMALL, ["enterprise_sso"], choices={"ai_use": level}))
        if level == "none":
            delta_none = with_sso - without
        else:
            assert with_sso - without == delta_none  # the SSO block is unknown-era in v6
    line = next(
        ln for ln in price(plan(SMALL, ["enterprise_sso"])).lines
        if ln.trace.component and ln.trace.component.catalog_key == "integration_sso_identity"
    )  # fmt: skip
    assert line.inputs["source_era"] == "unknown" and line.inputs["ai_saving"] == "not applied"


def test_simple_projects_get_only_what_they_ask_for() -> None:
    small = plan(SMALL)
    assert small.project_size == "small" and not small.scope
    assert not {"audit_trail_logging", "integration_sso_identity", "security_hardening"} & set(
        blocks(small)
    )
    audit = plan(SMALL, ["audit_log"])
    assert set(blocks(audit)) - set(blocks(small)) == {"audit_trail_logging"}
    assert (audit.project_size, audit.size_points) == (small.project_size, small.size_points)
    added = next(c for c in audit.components if c.key == "audit_trail_logging")
    assert added.size.value == "S" and added.label == "A record of who did what (audit log)"


@pytest.mark.parametrize(
    ("features", "scope", "message"),
    [
        (SMALL, ["no_such_item"], "unknown scope item"),
        (SMALL, ["forms_fee"], "features not ticked"),  # online forms not ticked
    ],
)
def test_bad_scope_is_refused(features: list[str], scope: list[str], message: str) -> None:
    with pytest.raises(HTTPException) as err:
        plan(features, scope)
    assert err.value.status_code == 422 and message in str(err.value.detail)


def test_every_scope_item_adds_existing_catalog_blocks() -> None:
    catalog = {c.key for c in REF["catalog"].components}
    for group in CFG.scope:
        for item in group.items:
            assert set(item.adds) <= catalog, item.key

"""Keyword reader fixes (OPEN_QUESTIONS 206): a barcode on a parcel is scanning, not stock;
stock is still found from its own words; an outside security audit is read without AI."""

from app.services.documents.parsing import Page, ParsedDocument
from app.services.extraction.basic_reader import basic_read
from app.services.quick.config import quick_config


def _keys(text: str) -> set[str]:
    doc = ParsedDocument(kind="text", pages=[Page(1, text)], approximate_pages=False)
    return {f.key for f in basic_read(quick_config(), doc).features}


def test_a_parcel_barcode_is_scanning_not_inventory() -> None:
    keys = _keys(
        "3.6 Drivers shall scan the barcode on every parcel at pickup and delivery "
        "with the phone camera."
    )
    assert "scanning" in keys
    assert "inventory" not in keys


def test_stock_is_still_inventory() -> None:
    assert "inventory" in _keys(
        "3.7 The pharmacy shall keep stock of medicines with batch numbers and expiry dates."
    )
    assert "inventory" in _keys(
        "The system shall manage the warehouse and record stock in and out."
    )


def _choices(text: str) -> dict[str, str]:
    doc = ParsedDocument(kind="text", pages=[Page(1, text)], approximate_pages=False)
    return {c.question: c.value for c in basic_read(quick_config(), doc).choices}


def test_a_security_audit_before_go_live_is_read_without_ai() -> None:
    asked = (
        "4.1 The platform shall pass a security audit by a CERT-In empanelled auditor "
        "before go-live."
    )
    assert _choices(asked).get("security_audit") == "yes"
    later = "A security audit is out of scope for this work."
    assert "security_audit" not in _choices(later)


def test_no_payment_gateway_is_needed_rules_payments_out() -> None:
    keys = _keys(
        "3.9 Settlement amounts shall be sent to the payments team's existing bank file system; "
        "no payment gateway is needed."
    )
    assert "payments" not in keys
    assert "payments" in _keys(
        "3.3 Parents shall pay school fees online through a payment gateway."
    )

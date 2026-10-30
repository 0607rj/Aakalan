"""Independent check (OPEN_QUESTIONS 140): a build estimate counted from what the system must
contain, compared with the priced build; the AI only lists items, the code counts."""

from decimal import Decimal

from app.services.documents.parsing import Page, ParsedDocument
from app.services.extraction.inventory import InventoryOutput, verify_inventory
from app.services.extraction.tender import FoundInventory, FoundItem, VerifiedEvidence
from app.services.quick.anchor import CheckLine, anchor_pd, independent_check
from app.services.quick.config import IndependentCheck, quick_config
from app.services.quick.reality import SupportRule, _support_share

D = Decimal
EV = [VerifiedEvidence(page=1, clause_ref="", quote="quoted")]


def rules() -> IndependentCheck:
    r = quick_config().independent_check
    assert r is not None
    return r


def items(*names: str, **extra: object) -> list[FoundItem]:
    return [FoundItem.model_validate({"name": n, "evidence": EV, **extra}) for n in names]


def clinic() -> FoundInventory:
    """The outside review's worked example: 6 records, 20 screens, 5 roles, no selected
    integration, 1 hard problem, several clinics on one system."""
    return FoundInventory(
        prompt_version="count_system_v1",
        entities=items(*(f"Record {i}" for i in range(6))),
        screens=items(*(f"Screen {i}" for i in range(20)), kind="single"),
        roles=items(*(f"Role {i}" for i in range(5))),
        integrations=items("SMS gateway", provider_selected=False),
        hard_problems=items("Slot booking", problem="concurrency", feature=""),
        tenancy="multi_tenant",
    )


def test_clinic_worked_example() -> None:
    """(6×6 + 20×3 + 5×2 + 0×8 + 1×12 + 6) × 1.35 = 124 × 1.35 = 167.4 pd ≈ 7.6 PM."""
    pd, counts, factors = anchor_pd(rules(), clinic())
    assert pd == D("167.4")
    assert {c.key: c.person_days for c in counts}["integrations"] == 0  # provider not chosen
    assert [f.value for f in factors] == [D("1.35")]  # no class factors read


def check(priced_pd: str, **kw: object) -> object:
    args: dict[str, object] = {
        "priced_pd": D(priced_pd),
        "pd_per_month": D(22),
        "project_size": "small",
        "top_lines": [CheckLine(label="Bookings", amount_paise=1)],
        "price_without_tax_paise": None,
        "emd_paise": None,
        "emd_rules": quick_config().reality_check,
        "confirmed_at": None,
        **kw,
    }
    inv = clinic().model_copy(update={"system_class": "booking_scheduling"})
    return independent_check(rules(), inv, **args)  # type: ignore[arg-type]


def test_gate_fires_on_the_clinic_run_and_not_close_to_the_count() -> None:
    high = check("594")  # the clinic run: 27 person-months against about 7.6
    assert high.flagged and high.direction == "high" and high.needs_confirmation  # type: ignore[attr-defined]
    assert high.band.position == "above"  # type: ignore[attr-defined]
    close = check("180")
    assert not close.flagged and not close.needs_confirmation  # type: ignore[attr-defined]
    assert close.band.position == "inside"  # type: ignore[attr-defined]
    assert check("60").direction == "low"  # type: ignore[attr-defined]


def test_emd_far_outside_needs_confirmation() -> None:
    """EMD ₹2.1 lakh implies ₹42 lakh to ₹1.05 crore; more than 2x above is blocked."""
    emd = 2_10_000_00
    ok = check("180", price_without_tax_paise=1_00_00_000_00, emd_paise=emd)
    assert not ok.emd_flagged and not ok.needs_confirmation  # type: ignore[attr-defined]
    far = check("180", price_without_tax_paise=2_50_00_000_00, emd_paise=emd)
    assert far.emd_flagged and far.needs_confirmation  # type: ignore[attr-defined]


def test_no_counts_no_check() -> None:
    out = independent_check(
        rules(),
        None,
        priced_pd=D(100),
        pd_per_month=D(22),
        project_size=None,
        top_lines=[],
        price_without_tax_paise=None,
        emd_paise=None,
        emd_rules=None,
        confirmed_at=None,
    )
    assert not out.available and not out.needs_confirmation


def test_counts_keep_only_quoted_items_once() -> None:
    doc = ParsedDocument(
        kind="pdf",
        pages=[Page(number=1, text="Patients book appointments with doctors at each clinic.")],
        approximate_pages=False,
    )
    quote = [{"page": 1, "clause_ref": "", "quote": "Patients book appointments with doctors"}]
    raw = InventoryOutput.model_validate(
        {
            "entities": [
                {"name": "Appointment", "evidence": quote},
                {"name": "appointment", "evidence": quote},  # same thing twice
                {"name": "Invoice", "evidence": [{**quote[0], "quote": "not on the page"}]},
            ],
            "hard_problems": [
                {"name": "Double booking", "problem": "concurrency", "feature": "booking_x",
                 "evidence": quote},
                {"name": "Magic", "problem": "teleport", "evidence": quote},
            ],
            "system_class": "booking_scheduling",
            "quality": "nonsense",
            "tenancy": "multi_tenant",  # no quote: single
        }
    )  # fmt: skip
    inv = verify_inventory(quick_config(), rules(), doc, raw)
    assert [e.name for e in inv.entities] == ["Appointment"]
    assert [h.problem for h in inv.hard_problems] == ["concurrency"]
    assert inv.hard_problems[0].feature == ""  # unknown feature key
    assert inv.system_class == "booking_scheduling" and inv.quality == ""
    assert inv.tenancy == "single"
    assert inv.dropped == 3


def test_support_warning_points_at_the_build() -> None:
    rule = SupportRule(
        ok=False,
        message="Year-1 maintenance is 14.2% of build cost; the industry rule of thumb is "
        "15–25%. Review the maintenance drivers.",
        below=True,
    )
    assert "build first" in _support_share(rule, "high").detail
    assert "support hours" in _support_share(rule, None).detail


def test_a_document_the_ai_read_but_could_not_count_waits_for_a_person() -> None:
    """OPEN_QUESTIONS 186: a failed count is a missing check, not a passed one."""
    base: dict[str, object] = {
        "priced_pd": D(100),
        "pd_per_month": D(22),
        "project_size": None,
        "top_lines": [],
        "price_without_tax_paise": None,
        "emd_paise": None,
        "emd_rules": quick_config().reality_check,
        "confirmed_at": None,
        "ai_read": True,
    }
    missing = independent_check(rules(), None, **base)  # type: ignore[arg-type]
    assert not missing.available and missing.needs_confirmation
    assert "could not be made" in (missing.reason or "")
    empty = clinic().model_copy(
        update={
            "entities": [],
            "screens": [],
            "roles": [],
            "integrations": [],
            "hard_problems": [],
            "tenancy": "single",
        }
    )
    too_little = independent_check(rules(), empty, **base)  # type: ignore[arg-type]
    assert not too_little.available and too_little.needs_confirmation
    # the EMD gate still works without the count
    emd = {"price_without_tax_paise": 2_50_00_000_00, "emd_paise": 2_10_000_00, "ai_read": False}
    far = independent_check(rules(), None, **{**base, **emd})  # type: ignore[arg-type]
    assert far.emd_flagged and far.needs_confirmation

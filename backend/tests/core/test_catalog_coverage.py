"""Where each representative requirement lands: a feature, a scope item, a standard building
block, a question, the user's own (generic) feature, or listed as not priced (no catalog block
and no effort source). Every mapping must point at something that exists, so a renamed or
removed key fails here instead of silently dropping work."""

from datetime import date

import pytest

from app.core.config import get_settings
from app.services.calibration.backtest import (
    LAYER_ORDER,
    BenchmarkSet,
    layer_shares,
    load_benchmarks,
    reference_for,
)
from app.services.quick.config import quick_config
from app.services.seeding.reference import load_reference

CFG = quick_config()
REF = reference_for(load_reference(get_settings().seeds_dir), "india")
FEATURES = {f.key for f in CFG.features}
SCOPE = {i.key for g in CFG.scope for i in g.items}
STANDARD = {k for t in CFG.sizing.tiers for k in t.base_components}
QUESTIONS = {(k, str(o.value)) for k, q in CFG.questions.items() for o in q.options}
CUSTOM = set(CFG.custom_feature_types)
NOT_PRICED = set(CFG.not_priced_topics)

# (requirement, how it is covered, key). Coverage, not effort: the hours come from the catalog.
COVERAGE = [
    ("Public website with pages the staff can edit", "feature", "public_website"),
    ("Records: create, edit, list and delete", "custom", "module"),
    ("Online application forms with uploads", "feature", "online_forms"),
    ("Several client organisations on one system (SaaS)", "not_priced", "multi_tenancy"),
    ("Online store with cart and checkout", "feature", "online_store"),
    ("Subscriptions and recurring billing", "scope", "subscriptions"),
    ("Online payments", "feature", "payments"),
    ("Doctor appointment booking", "feature", "bookings"),
    ("Video consultations", "not_priced", "realtime_media"),
    ("Health-record standards (FHIR, ABDM)", "not_priced", "health_standards"),
    ("Job applications move through review steps", "feature", "approval_workflow"),
    ("Marketplace payouts to sellers", "feature", "marketplace"),  # catalog v7 block
    ("AI chatbot answering from documents", "feature", "ai_chatbot"),
    ("Reading uploaded documents with an LLM", "custom", "ai"),
    ("Basic sign-in, roles and permissions", "standard", "user_management_rbac"),
    ("Two-step sign-in (MFA)", "scope", "two_step_sign_in"),
    ("Organisation single sign-on (SAML / AD)", "scope", "enterprise_sso"),
    ("Aadhaar e-KYC", "scope", "forms_ekyc"),
    ("An API or webhooks for other systems", "scope", "public_api"),
    ("Connecting existing software", "question", "integrations:one_two"),
    ("Regular data import from another system", "scope", "data_import"),
    ("Reports and dashboards", "feature", "dashboards"),
    ("Moving old data", "question", "old_data:little"),
    ("Hosting, backups and disaster recovery", "question", "availability:high"),
    ("CI / CD and environments", "standard", "devops_cicd_setup"),
    ("Security audit and fixing its findings", "question", "security_audit:yes"),
    ("Accessibility (GIGW / WCAG)", "feature", "accessibility"),
    ("Testing and user acceptance", "standard", "functional_testing_uat_support"),
    ("Audit log of who did what", "scope", "audit_log"),
    ("WhatsApp notifications", "scope", "whatsapp"),
    ("Digital signatures", "scope", "documents_esign"),
]


@pytest.mark.parametrize(("requirement", "kind", "key"), COVERAGE)
def test_every_representative_requirement_has_a_home(requirement: str, kind: str, key: str) -> None:
    where = {
        "feature": FEATURES,
        "scope": SCOPE,
        "standard": STANDARD,
        "custom": CUSTOM,
        "not_priced": NOT_PRICED,
        "question": {f"{q}:{v}" for q, v in QUESTIONS},
    }[kind]
    assert key in where, f"{requirement}: {kind} {key!r} does not exist"


def test_new_items_reuse_sourced_blocks_and_say_so() -> None:
    """Coverage added without new effort numbers: each item maps to an existing catalog block;
    items whose work the block only partly covers say so."""
    catalog = {c.key: c for c in REF["catalog"].components}
    for group in CFG.scope:
        for item in group.items:
            assert set(item.adds) <= set(catalog), item.key
            if item.partly_priced:
                assert item.note, item.key


def test_layer_shares_add_up_and_show_fixed_blocks_weigh_more_when_small() -> None:
    """The diagnostic behind the size-bias finding: on small projects the standard building
    blocks are a bigger share of the cost than on large ones (a fixed set per project)."""
    bench = load_benchmarks(get_settings().seeds_dir / "benchmarks" / "india.yaml")
    pick: list[str] = []
    for size in ("small", "large"):
        pick += [b.id for b in bench.projects if b.use and b.model.size == size][:3]
    subset = BenchmarkSet.model_validate(
        {**bench.model_dump(), "projects": [b.model_dump() for b in bench.projects if b.id in pick]}
    )
    shares = layer_shares(CFG, subset, REF, as_of=date(2026, 10, 19))
    for layers in shares.values():
        assert set(layers) <= set(LAYER_ORDER)
    assert shares["small"]["standard blocks"] > shares["large"]["standard blocks"]

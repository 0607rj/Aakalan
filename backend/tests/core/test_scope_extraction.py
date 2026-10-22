# ruff: noqa: E501  (inline document text)
"""Scope found in a document or description, read in context: asked for, probably needed,
ruled out, for later, or only mentioned. Only the first two are offered, none is ticked, and
only what the user ticks is priced. AI-path tests use a fake client: they check the handling of
what an LLM returns, not how well a real model reads documents."""

from types import SimpleNamespace
from typing import Any

import pytest

from app.llm.client import FakeClient, set_llm_client
from app.services.documents.parsing import Page, ParsedDocument
from app.services.extraction.basic_reader import basic_read, scope_status
from app.services.extraction.describe import suggest_features
from app.services.extraction.merge import merge_extractions
from app.services.extraction.tender import ai_read, build_prompt, verify_findings
from app.services.quick.config import quick_config

CFG = quick_config()


def doc(*pages: str) -> ParsedDocument:
    return ParsedDocument(
        kind="text", pages=[Page(i + 1, t) for i, t in enumerate(pages)], approximate_pages=False
    )


def read(*pages: str) -> Any:
    d = doc(*pages)
    return verify_findings(CFG, d, basic_read(CFG, d), reader="basic", version="test")


@pytest.mark.parametrize(
    ("sentence", "status"),
    [
        ("All officials shall sign in through two-factor authentication.", "explicit"),
        ("Two-factor authentication is not required for citizens.", "excluded"),
        ("The vendor shall not build two-factor authentication.", "excluded"),
        ("Two-factor authentication may be considered in phase 2.", "future"),
        ("An optional two-factor authentication module.", "future"),
        ("The old portal had two-factor authentication.", "background"),
        ("Two-factor authentication for officers.", "inferred"),
        ("Two-factor authentication is not included in this release.", "excluded"),
    ],
)
def test_sentence_decides_the_status(sentence: str, status: str) -> None:
    assert scope_status(sentence) == status


def test_ruled_out_and_later_items_are_set_aside_not_offered() -> None:
    ex = read(
        "1.1 Staff shall sign in with two-factor authentication.\n"
        "1.2 WhatsApp messages are out of scope.\n"
        "1.3 A public API with webhooks may be added in a later phase.\n"
        "1.4 The department will send SMS notifications to applicants."
    )
    offered = {s.key: s.status for s in ex.scope}
    aside = {s.key: s.status for s in ex.scope_set_aside}
    assert offered == {"two_step_sign_in": "explicit"}
    # the SMS line finds the notifications feature, so its WhatsApp item applies: ruled out
    assert aside == {"public_api": "future", "whatsapp": "excluded"}
    assert all(s.evidence and s.evidence[0].page == 1 for s in ex.scope + ex.scope_set_aside)


def test_asked_for_somewhere_wins_over_ruled_out_elsewhere() -> None:
    ex = read(
        "Two-factor authentication is not required for citizens.",
        "Officers must use two-factor authentication.",
    )
    assert [(s.key, s.status) for s in ex.scope] == [("two_step_sign_in", "explicit")]
    assert ex.scope_set_aside == []


def ev(quote: str) -> list[dict[str, object]]:
    return [{"page": 1, "clause_ref": "", "quote": quote}]


def test_ai_reader_scope_is_checked_and_sorted() -> None:
    """Unknown keys and quotes not on the page are dropped; ruled-out, later and background
    items are set aside; nothing is ticked (the form decides)."""
    pages = [
        "2.1 Officers shall use two-factor authentication.\n"
        "2.2 Integration with payment gateway will be taken up in phase 2.\n"
        "2.3 The present system sends SMS alerts to applicants.\n"
        "2.4 Audit logs are not required."
    ]

    def responder(system: str, user: str) -> object:
        assert "two_step_sign_in" in system and "excluded:" in system  # the v5 rules
        assert "Never estimate" in system
        return {
            "project_name": "Portal", "summary": "", "features": [], "other_features": [],
            "choices": [], "numbers": [], "unclear_points": [],
            "scope": [
                {"key": "two_step_sign_in", "status": "explicit", "evidence": ev("Officers shall use two-factor authentication")},
                {"key": "otp_codes", "status": "background", "evidence": ev("The present system sends SMS alerts to applicants")},
                {"key": "audit_log", "status": "excluded", "evidence": ev("Audit logs are not required")},
                {"key": "social_login", "status": "inferred", "note": "Citizens sign in often", "evidence": ev("this quote is not in the document")},
                {"key": "teleport", "status": "explicit", "evidence": ev("Officers shall use two-factor authentication")},
            ],
        }  # fmt: skip

    d = doc(*pages)
    result = ai_read(FakeClient(responder), CFG, d).output
    ex = verify_findings(CFG, d, result, reader="ai", version="test")
    assert [(s.key, s.status) for s in ex.scope] == [("two_step_sign_in", "explicit")]
    assert {s.key: s.status for s in ex.scope_set_aside} == {
        "otp_codes": "background",
        "audit_log": "excluded",
    }
    assert ex.dropped_findings == 2  # invented quote, unknown key


def test_prompt_lists_every_scope_item_and_the_status_rules() -> None:
    prompt = build_prompt(CFG)
    for group in CFG.scope:
        for item in group.items:
            assert f"- {item.key}: " in prompt
    for status in ("explicit:", "inferred:", "excluded:", "future:", "background:"):
        assert status in prompt


def test_a_corrigendum_can_rule_an_item_out() -> None:
    rfp = read("Staff shall sign in with two-factor authentication.")
    corrigendum = read("Two-factor authentication is not required.")
    first = SimpleNamespace(kind="rfp", filename="rfp.pdf")
    later = SimpleNamespace(kind="corrigendum", filename="corr.pdf")
    merged, _ = merge_extractions([(first, rfp), (later, corrigendum)])  # type: ignore[list-item]
    assert merged.scope == [] and [s.key for s in merged.scope_set_aside] == ["two_step_sign_in"]
    again, _ = merge_extractions([(first, corrigendum), (first, rfp)])  # type: ignore[list-item]
    assert [s.key for s in again.scope] == ["two_step_sign_in"]  # an RFP line asking for it


def test_typed_description_without_a_key_uses_the_basic_reader() -> None:
    """No API key: the keyword reader runs and says so; nothing calls a real LLM."""
    set_llm_client(None)
    s = suggest_features(CFG, "Doctors book slots. Two-factor authentication is not needed.")
    assert s.reader == "basic" and s.note
    assert "two_step_sign_in" not in {i.key for i in s.scope}  # ruled out in the words


def test_unpriced_capabilities_are_listed_not_guessed() -> None:
    ex = read(
        "The platform shall be multi-tenant for several hospitals.\n"
        "Doctors shall hold video consultations with patients.\n"
        "Records shall follow HL7 FHIR standards."
    )
    assert {"multi_tenancy", "realtime_media", "health_standards"} <= {
        n.topic for n in ex.not_priced
    }

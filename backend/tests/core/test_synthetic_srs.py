"""Five synthetic SRS documents (tests/fixtures/srs) against expected-results manifests written
from each document's meaning and the quick config, not from an extractor's output.

They check functional behaviour without an API key: the keyword (basic) reader, the handling of
what an AI reader returns (a fake client), merging with a corrigendum, and how confirmed scope is
planned and priced. A fake AI client proves nothing about how well a real model reads documents.
"""

import re
from datetime import date
from functools import cache
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
import yaml

from app.core.config import get_settings
from app.llm.client import FakeClient, LLMNotConfiguredError, get_llm_client, set_llm_client
from app.services.calibration.backtest import reference_for
from app.services.documents.parsing import Page, ParsedDocument
from app.services.engine.core import calculate
from app.services.extraction.basic_reader import basic_read
from app.services.extraction.merge import merge_extractions
from app.services.extraction.tender import TenderExtraction, ai_read, verify_findings
from app.services.quick.config import quick_config
from app.services.quick.service import QuickPlan, QuickRequest, plan_quick, plan_to_input
from app.services.seeding.reference import load_reference

SRS = Path(__file__).parents[1] / "fixtures" / "srs"
MANIFESTS = sorted(p.name for p in SRS.glob("*.expected.yaml"))
CFG = quick_config()
REF = reference_for(load_reference(get_settings().seeds_dir), "india")
REF["clarity"] = CFG.requirement_clarity
SET_ASIDE = ("excluded", "future", "background")
SCOPE_ITEMS = {i.key: i for g in CFG.scope for i in g.items}


@cache
def manifest(name: str) -> dict[str, Any]:
    data: dict[str, Any] = yaml.safe_load((SRS / name).read_text(encoding="utf-8"))
    return data


def pages(md: str) -> list[str]:
    return (SRS / md).read_text(encoding="utf-8").split("<!-- page -->")


def document(md: str) -> ParsedDocument:
    return ParsedDocument(
        kind="text",
        pages=[Page(i + 1, t) for i, t in enumerate(pages(md))],
        approximate_pages=False,
    )


@cache
def basic(md: str) -> TenderExtraction:
    d = document(md)
    return verify_findings(CFG, d, basic_read(CFG, d), reader="basic", version="test")


def scope_reqs(m: dict[str, Any]) -> list[dict[str, Any]]:
    return [r for r in m["requirements"] if r["kind"] == "scope"]


def offered_scope(m: dict[str, Any]) -> list[str]:
    return list(dict.fromkeys(r["key"] for r in scope_reqs(m) if r["offered"]))


def plan(m: dict[str, Any], scope: list[str], extraction: Any = None) -> QuickPlan:
    req = QuickRequest(name=m["project"], features=m["features"], scope=scope)
    return plan_quick(CFG, req, extraction, m["document"])


def blocks(p: QuickPlan) -> list[tuple[str, str, str | None]]:
    return sorted((c.key, c.size.value, c.label) for c in p.components)


@pytest.mark.parametrize("name", MANIFESTS)
def test_manifest_points_at_real_config(name: str) -> None:
    m = manifest(name)
    features = {f.key for f in CFG.features}
    assert set(m["features"]) | set(m["not_features"]) <= features
    assert set(m["not_priced"]) | set(m["not_listed"]) <= set(CFG.not_priced_topics)
    for q, v in m["choices"].items():
        CFG.questions[q].option(v)
    homes: dict[str, set[Any]] = {
        "feature": features,
        "scope": set(SCOPE_ITEMS),
        "not_priced": set(CFG.not_priced_topics),
        "standard": {k for t in CFG.sizing.tiers for k in t.base_components},
        "unmapped": {None},
    }
    for r in m["requirements"]:
        assert r["key"] in homes[r["kind"]], r["id"]
        if r["kind"] == "scope" and r["offered"]:  # disclosed for what can be priced
            assert bool(r.get("partly_priced")) == SCOPE_ITEMS[r["key"]].partly_priced, r["id"]


# --- deterministic (basic) reader ----------------------------------------------------------


@pytest.mark.parametrize("name", MANIFESTS)
def test_basic_reader_features_choices_and_not_priced(name: str) -> None:
    m = manifest(name)
    ex = basic(m["document"])
    ticked = {f.key for f in ex.features if f.suggested}
    assert set(m["features"]) <= ticked
    assert not set(m["not_features"]) & {f.key for f in ex.features}  # not even offered
    for q, v in m["choices"].items():
        assert ex.choices[q].value == v, q
    topics = {n.topic for n in ex.not_priced}
    assert set(m["not_priced"]) <= topics
    assert not set(m["not_listed"]) & topics
    assert len(ex.unclear_points) >= m.get("min_unclear_points", 0)


@pytest.mark.parametrize("name", MANIFESTS)
def test_basic_reader_offers_only_what_is_asked_for(name: str) -> None:
    m = manifest(name)
    ex = basic(m["document"])
    offered = {s.key: s.status for s in ex.scope}
    aside = {s.key: s.status for s in ex.scope_set_aside}
    for r in scope_reqs(m):
        if r["offered"] and r.get("pricing") == "already_included" and r["key"] not in offered:
            # its sentence already prices a ticked feature: not offered again (no double count)
            assert r["key"] not in aside, r["id"]
        elif r["offered"]:
            assert offered.get(r["key"]) == r["classification"], r["id"]
        else:
            assert r["key"] not in offered, r["id"]
            if r.get("detect") != "optional":
                assert aside.get(r["key"]) == r["classification"], r["id"]


# --- AI reader handling (fake client) ------------------------------------------------------


def clause_quote(md: str, clause: str) -> tuple[int, str]:
    """The document's own sentence for a clause number (e.g. "3.4"), and its page."""
    for n, text in enumerate(pages(md), 1):
        hit = re.search(rf"(?m)^{re.escape(clause)} (.+)$", text)
        if hit:
            return n, hit.group(1).strip()
    raise AssertionError(f"clause {clause} not in {md}")


@pytest.mark.parametrize("name", MANIFESTS)
def test_ai_reader_answers_are_sorted_by_status(name: str) -> None:
    """Given the statuses the manifest expects, the pipeline offers exactly the asked-for items
    and sets the rest aside; it does not judge how well a real model would read the text."""
    m = manifest(name)
    findings = []
    for r in scope_reqs(m):
        page, quote = clause_quote(m["document"], r["id"].split("-", 1)[1].rstrip("bc"))
        findings.append(
            {
                "key": r["key"],
                "status": r["classification"],
                "evidence": [{"page": page, "clause_ref": "", "quote": quote}],
            }
        )

    def responder(system: str, user: str) -> object:
        return {
            "project_name": m["project"], "summary": "", "features": [], "other_features": [],
            "choices": [], "numbers": [], "unclear_points": [], "scope": findings,
        }  # fmt: skip

    d = document(m["document"])
    ex = verify_findings(
        CFG, d, ai_read(FakeClient(responder), CFG, d).output, reader="ai", version="test"
    )
    assert {s.key for s in ex.scope} == set(offered_scope(m))
    expected_aside = {r["key"] for r in scope_reqs(m) if r["classification"] in SET_ASIDE} - set(
        offered_scope(m)
    )
    assert {s.key for s in ex.scope_set_aside} == expected_aside


def test_corrigendum_rules_an_item_out() -> None:
    m = manifest("enterprise_erp.expected.yaml")
    rfp, corr = basic(m["document"]), basic(m["corrigendum"])
    merged, _ = merge_extractions(
        [
            (SimpleNamespace(kind="rfp", filename=m["document"]), rfp),  # type: ignore[list-item]
            (SimpleNamespace(kind="corrigendum", filename=m["corrigendum"]), corr),  # type: ignore[list-item]
        ]
    )
    offered = {s.key for s in merged.scope}
    for key in m["corrigendum_removes"]:
        assert key in {s.key for s in rfp.scope} and key not in offered
        assert key in {s.key for s in merged.scope_set_aside}


def test_missing_api_key_blocks_only_the_ai_reader() -> None:
    """No key (tests blank it): asking for a client fails clearly, with no network call, and the
    keyword reader still reads the documents."""
    set_llm_client(None)
    with pytest.raises(LLMNotConfiguredError):
        get_llm_client()
    assert basic("clinic_management.md").reader == "basic"


# --- estimation ----------------------------------------------------------------------------


@pytest.mark.parametrize("name", MANIFESTS)
def test_confirmed_scope_adds_only_new_work(name: str) -> None:
    """Each confirmed item adds blocks only when they are not already in the project; the
    manifest says which (adds_work / already_included)."""
    m = manifest(name)
    chosen = offered_scope(m)
    full = blocks(plan(m, chosen))
    for r in scope_reqs(m):
        if not r["offered"]:
            continue
        without = blocks(plan(m, [k for k in chosen if k != r["key"]]))
        added = len(full) > len(without) or full != without
        assert added == (r["pricing"] == "adds_work"), r["id"]


@pytest.mark.parametrize("name", MANIFESTS)
def test_suggested_but_unticked_scope_never_changes_the_price(name: str) -> None:
    m = manifest(name)
    ex = basic(m["document"]).model_dump(mode="json")
    from_document, by_hand = plan(m, [], ex), plan(m, [])
    assert blocks(from_document) == blocks(by_hand)
    # answers the document left open widen the range (OPEN_QUESTIONS 139): a separate effect
    assert from_document.clarity <= by_hand.clarity
    from_document.clarity = by_hand.clarity
    a = calculate(plan_to_input(from_document, "x", REF, date(2026, 10, 19), 3, 300))
    b = calculate(plan_to_input(by_hand, "x", REF, date(2026, 10, 19), 3, 300))
    assert a.totals == b.totals


@pytest.mark.parametrize("name", MANIFESTS)
def test_planning_is_deterministic_whatever_the_order(name: str) -> None:
    m = manifest(name)
    chosen = offered_scope(m)
    one = calculate(plan_to_input(plan(m, chosen), "x", REF, date(2026, 10, 19), 3, 300))
    other = calculate(
        plan_to_input(plan(m, list(reversed(chosen))), "x", REF, date(2026, 10, 19), 3, 300)
    )
    assert one.model_dump_json() == other.model_dump_json()


def test_separate_integrations_stay_separate() -> None:
    """The ERP's vendor webhooks, digital signatures and nightly bank import are three
    different systems: three blocks, not one shared block."""
    m = manifest("enterprise_erp.expected.yaml")
    p = plan(m, offered_scope(m))
    labels = {c.label for c in p.components if c.key == "custom_integration"}
    assert {
        "An API or webhooks so other systems can use it",
        "Digital signatures (eSign or DSC)",
        "Regular data import or sync from another system",
    } <= labels

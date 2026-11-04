"""'Usually needed for this kind of software' (OPEN_QUESTIONS 207): the AI names modules the
words never mention; the code keeps only real, new ones; the engine prices each one; nothing is
ticked for the user."""

from typing import Any

from fastapi.testclient import TestClient

from app.llm.client import FakeClient, set_llm_client
from app.services.documents.parsing import Page, ParsedDocument
from app.services.extraction.tender import ai_read, verify_findings
from app.services.quick.config import quick_config

H = dict[str, str]
CFG = quick_config()
TEXT = "A school system where parents pay the fees online and see their child's attendance."
PAY = {
    "key": "payments",
    "evidence": [{"page": 1, "clause_ref": "", "quote": "pay the fees online"}],
}


def _custom(name: str, why: str = "Schools usually have it.", **more: Any) -> dict[str, Any]:
    return {"name": name, "category": "module", "size": "M", "why": why, **more}


SUGGESTED = [
    {"feature": "notifications", "why": "Parents get fee reminders by SMS before the due date."},
    {"feature": "payments", "why": "Already asked for: dropped."},
    {"feature": "dashboards", "why": "Too basic: dropped."},
    {"feature": "no_such_key", "why": "Not a listed feature: dropped."},
    {"feature": "mobile_app", "why": "Parents check fees and attendance on their phone."},
    _custom("Admin login", "Basic: dropped."),
    _custom("Exams and report cards", "Teachers enter marks and the system makes report cards."),
    _custom("Exams and report cards", "A repeat: dropped."),
    {"feature": "maps", "why": "Parents see the school bus on a map."},
    {"feature": "online_forms", "why": "Admissions online."},
    {"feature": "bookings", "why": "Class bookings."},
]  # fmt: skip


def _raw(suggested: list[dict[str, Any]], choices: list[Any] | None = None) -> dict[str, Any]:
    return {
        "project_name": "School", "summary": "", "features": [PAY], "other_features": [],
        "choices": choices or [], "numbers": [], "unclear_points": [],
        "industry_suggestions": suggested,
    }  # fmt: skip


def _read(raw: dict[str, Any], text: str = TEXT) -> Any:
    doc = ParsedDocument(kind="text", pages=[Page(1, text)], approximate_pages=False)
    client = FakeClient(lambda s, u: {"other_features": []} if "<already_found>" in u else raw)
    return verify_findings(CFG, doc, ai_read(client, CFG, doc).output, reader="ai", version="t")


def test_only_new_real_modules_are_kept() -> None:
    ex = _read(_raw(SUGGESTED))
    got = [s.feature or s.label for s in ex.industry_suggestions]
    want = ["notifications", "mobile_app", "Exams and report cards", "maps", "online_forms"]
    assert got == [*want, "bookings"]
    assert ex.industry_suggestions_asked
    custom = ex.industry_suggestions[2]
    assert (custom.category, custom.size) == ("module", "M")
    assert ex.industry_suggestions[0].label == CFG.feature("notifications").label
    assert "notifications" not in {f.key for f in ex.features}  # offered, never ticked


def test_a_feature_an_answer_already_adds_is_not_suggested() -> None:
    quote = "Parents shall also use an Android and iPhone app."
    app = [{"question": "platforms", "value": "web_mobile",
            "evidence": [{"page": 1, "clause_ref": "", "quote": quote}]}]  # fmt: skip
    ex = _read(_raw(SUGGESTED, app), f"{TEXT}\n{quote}")
    assert "mobile_app" not in {s.feature for s in ex.industry_suggestions}


def test_the_description_flow_offers_them_and_drops_what_the_words_rule_out(
    client: TestClient, admin_headers: H
) -> None:
    text = f"{TEXT} We do not need a mobile app."
    set_llm_client(FakeClient(lambda s, u: {"other_features": []} if "<already_found>" in u
                              else _raw(SUGGESTED)))  # fmt: skip
    try:
        r = client.post("/quick-estimate/suggest", json={"text": text}, headers=admin_headers)
    finally:
        set_llm_client(None)
    assert r.status_code == 200, r.text
    body = r.json()
    keys = [s["feature"] or s["label"] for s in body["industry_suggestions"]]
    assert "mobile_app" not in keys  # "do not need a mobile app"
    assert keys[0] == "notifications" and "Exams and report cards" in keys
    assert "notifications" not in {f["key"] for f in body["features"]}
    # the ask no finding quotes is listed; the clause that rules the app out is not (210)
    assert body["unmatched"] == ["see their child's attendance"]


def test_no_ai_key_gives_no_suggestions(client: TestClient, admin_headers: H) -> None:
    r = client.post("/quick-estimate/suggest", json={"text": TEXT}, headers=admin_headers)
    assert r.status_code == 200 and r.json()["reader"] == "basic"
    assert r.json()["industry_suggestions"] == []  # the form shows the fixed short list
    assert not r.json()["industry_suggestions_asked"]


def test_the_engine_prices_what_each_one_adds(client: TestClient, admin_headers: H) -> None:
    form = {"name": "School", "features": ["payments", "online_forms"]}
    suggestions = [
        {"feature": "maps", "label": "Maps", "why": "Bus tracking."},
        {"feature": "mobile_app", "label": "Mobile app", "why": "Parents use phones."},
        {"feature": "online_forms", "label": "Online forms", "why": "Already ticked."},
        {"feature": "", "label": "Exams and report cards", "why": "Marks.", "category": "module",
         "size": "M"},
    ]  # fmt: skip
    body = {"request": form, "suggestions": suggestions}

    def prices() -> list[int | None]:
        r = client.post("/quick-estimate/suggestion-prices", json=body, headers=admin_headers)
        assert r.status_code == 200, r.text
        return [p["adds_paise"] for p in r.json()]

    first = prices()
    maps, app, ticked, custom = first
    assert maps and app and custom and maps > 0 and app > maps  # an app is more work than maps
    assert ticked == 0
    assert prices() == first  # fixed seed: the same form gives the same figures


def test_at_most_the_configured_number_and_none_when_all_is_asked_for() -> None:
    limit = CFG.industry_suggestions.max_items if CFG.industry_suggestions else 0
    many = [_custom(f"Module number {chr(65 + i)}") for i in range(limit + 3)]
    assert len(_read(_raw(many)).industry_suggestions) == limit
    none = _read(_raw([]))
    assert none.industry_suggestions == [] and none.industry_suggestions_asked


def test_ready_made_is_noted_only_when_the_ai_says_it_is_common() -> None:
    """Shown beside the build-type prices (OPEN_QUESTIONS 209); never an answer or a price."""
    note = "School management software is widely sold as ready products set up for each school."
    common = _read({**_raw([]), "ready_made": {"common": True, "note": note}})
    assert common.ready_made is not None and common.ready_made.note == note
    assert "build_type" not in common.choices  # the user decides how it is built
    assert _read({**_raw([]), "ready_made": {"common": False, "note": ""}}).ready_made is None
    assert _read({**_raw([]), "ready_made": {"common": True, "note": " "}}).ready_made is None
    assert _read(_raw([])).ready_made is None  # readings without it load as before

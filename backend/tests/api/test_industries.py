"""The manual form's "What is it for?" (OPEN_QUESTIONS 212): each industry offers its popular
features, unticked, each priced by the engine; browse all is grouped by purpose."""

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.services.quick.config import QuickConfig, quick_config

H = dict[str, str]
CFG = quick_config()


def _options(client: TestClient, headers: H) -> dict[str, Any]:
    r = client.get("/quick-estimate/options", headers=headers)
    assert r.status_code == 200, r.text
    body: dict[str, Any] = r.json()
    return body


def test_each_industry_offers_its_popular_features(client: TestClient, admin_headers: H) -> None:
    options = _options(client, admin_headers)
    industries = {i["key"]: i for i in options["industries"]}
    assert len(industries) >= 10
    kinds = {t["key"] for t in options["project_types"]}
    labels = {f["key"]: f["label"] for f in options["features"]}
    for ind in industries.values():
        assert ind["project_type"] in kinds and 0 < len(ind["suggestions"]) <= 12
        for s in ind["suggestions"]:
            assert s["why"]
            if s["feature"]:  # a listed feature keeps its own name
                assert s["label"] == labels[s["feature"]] and not s["category"]
            else:  # a module the list lacks: priced as the user's own feature
                assert s["label"] and s["category"] and s["size"] in {"S", "M", "L"}
        # its 1-3 main features are ticked when it is picked; the rest are offered
        assert 1 <= len(ind["ticked"]) <= 3
        assert set(ind["ticked"]) <= {s["label"] for s in ind["suggestions"]}
    school = [s["label"] for s in industries["school"]["suggestions"]]
    assert "Daily attendance" in school and "Online fee payment" in school
    assert industries["edtech"]["tag"] == "EdTech" and industries["fintech"]["tag"] == "FinTech"
    assert "Courses and lessons" in industries["edtech"]["ticked"]


def test_browse_all_groups_cover_known_features(client: TestClient, admin_headers: H) -> None:
    options = _options(client, admin_headers)
    keys = {f["key"] for f in options["features"]}
    grouped = [k for g in options["feature_groups"] for k in g["features"]]
    assert grouped and set(grouped) <= keys
    assert len(grouped) == len(set(grouped))  # each feature in one group only


def test_an_industry_list_is_priced_by_the_engine(client: TestClient, admin_headers: H) -> None:
    options = _options(client, admin_headers)
    school = next(i for i in options["industries"] if i["key"] == "school")
    form = {"name": "School", "project_type": school["project_type"], "features": ["payments"]}
    body = {"request": form, "suggestions": school["suggestions"]}
    r = client.post("/quick-estimate/suggestion-prices", json=body, headers=admin_headers)
    assert r.status_code == 200, r.text
    adds = {p["label"]: p["adds_paise"] for p in r.json()}
    assert adds["Online fee payment"] == 0  # already ticked
    assert adds["Daily attendance"] and adds["Daily attendance"] > 0
    # a large module is more work than a small one
    assert adds["Exams, marks and report cards"] > adds["Class timetable"] > 0


def test_a_wrong_industry_list_is_refused() -> None:
    raw = CFG.model_dump(mode="json")
    item = raw["industries"]["items"][0]
    bad_feature = {**item, "features": [{"feature": "no_such_feature", "why": "x"}]}
    with pytest.raises(ValueError, match="unknown feature"):
        QuickConfig.model_validate(
            {**raw, "industries": {**raw["industries"], "items": [bad_feature]}}
        )
    bad_module = {**item, "features": [{"name": "Thing", "category": "nope", "why": "x"}]}
    with pytest.raises(ValueError, match="needs a name and a type"):
        QuickConfig.model_validate(
            {**raw, "industries": {**raw["industries"], "items": [bad_module]}}
        )

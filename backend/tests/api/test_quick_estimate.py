"""Quick estimate: plain form -> priced estimate -> plain summary."""

from typing import Any

from fastapi.testclient import TestClient

from app.services.quick.config import quick_config

H = dict[str, str]


def quick(client: TestClient, headers: H, **body: Any) -> Any:
    payload = {"name": "Quick test portal", "features": ["online_forms", "ai_chatbot"], **body}
    return client.post("/quick-estimates", json=payload, headers=headers)


def test_options_are_plain_language(client: TestClient, admin_headers: H) -> None:
    r = client.get("/quick-estimate/options", headers=admin_headers)
    assert r.status_code == 200
    body = r.json()
    assert {f["key"] for f in body["features"]} >= {"online_forms", "ai_chatbot", "payments"}
    scale = next(q for q in body["questions"] if q["key"] == "scale")
    assert scale["default"] == "up_to_10k" and len(scale["options"]) == 7
    assert scale["options"][-1]["unsure"]  # every key question can be answered "Not sure"
    mains = [q["key"] for q in body["questions"] if q["group"] == "main"]
    assert mains[:3] == ["version", "platforms", "scale"]
    assert "ai_use" not in {q["key"] for q in body["questions"]}  # a company setting
    ticks = {f["key"] for f in body["features"] if not f["hidden"]}
    assert not ticks & {"mobile_app", "connect_existing", "old_data"}  # asked as questions


def test_quick_estimate_summary(client: TestClient, admin_headers: H) -> None:
    r = quick(client, admin_headers, choices={"scale": "up_to_10k", "support_years": 3})
    assert r.status_code == 201, r.text
    s = r.json()
    assert s["feasible"] and s["indicative"]
    assert s["low_paise"] <= s["likely_paise"] <= s["high_paise"]
    assert sum(p["amount_paise"] for p in s["parts"]) == s["planned_paise"]
    assert s["risk_allowance_paise"] == s["likely_paise"] - s["planned_paise"]
    run = next(p for p in s["parts"] if p["key"] == "run")
    assert s["support_years"] == 3 and "3 years" in run["label"]
    assert s["biggest_uncertainty"].startswith("The biggest unknown is")
    assert s["features"][0].startswith("Online application")
    # the detailed estimate is the same engine output, with ticked features as requirements
    detail = client.get(f"/estimates/{s['estimate_id']}", headers=admin_headers).json()
    assert detail["p50_paise"] == s["likely_paise"]
    chatbot = next(ln for ln in detail["lines"] if ln["bucket"] == "build.ai_ml")
    trace = client.get(
        f"/estimates/{s['estimate_id']}/lines/{chatbot['id']}/trace", headers=admin_headers
    ).json()["trace"]
    assert trace["requirements"][0]["clause_ref"].startswith("Feature: AI chatbot")
    again = client.get(f"/estimates/{s['estimate_id']}/summary", headers=admin_headers).json()
    assert again["likely_paise"] == s["likely_paise"]


def test_more_features_cost_more(client: TestClient, admin_headers: H) -> None:
    few = quick(client, admin_headers, features=["online_forms"]).json()
    many = quick(
        client, admin_headers, features=["online_forms", "approval_workflow", "payments"]
    ).json()
    assert many["planned_paise"] > few["planned_paise"]


def test_no_chatbot_means_no_ai_running_cost(client: TestClient, admin_headers: H) -> None:
    s = quick(client, admin_headers, features=["online_forms"]).json()
    detail = client.get(f"/estimates/{s['estimate_id']}", headers=admin_headers).json()
    assert not [ln for ln in detail["lines"] if ln["bucket"] == "run.ai_runtime"]


def test_bad_input_is_rejected(client: TestClient, admin_headers: H) -> None:
    assert quick(client, admin_headers, features=["teleport"]).status_code == 422
    assert quick(client, admin_headers, choices={"scale": "huge"}).status_code == 422
    assert quick(client, admin_headers, choices={"colour": "blue"}).status_code == 422
    assert quick(client, admin_headers, features=[]).status_code == 422
    bad_type = [{"name": "X", "category": "spaceship", "size": "M"}]
    assert quick(client, admin_headers, features=[], custom_features=bad_type).status_code == 422


def test_impossible_deadline_is_explained(client: TestClient, admin_headers: H) -> None:
    features = ["online_forms", "approval_workflow", "documents", "dashboards", "payments", "crm"]
    s = quick(
        client, admin_headers, features=features, deadline_months=1, choices={"scale": "over_10l"},
        feature_levels=dict.fromkeys(features, "advanced"),
    ).json()  # fmt: skip
    assert not s["feasible"] and s["likely_paise"] is None and "deadline" in s["message"]


def test_list_shows_latest_estimates(client: TestClient, admin_headers: H) -> None:
    quick(client, admin_headers, name="Listed portal")
    names = [s["name"] for s in client.get("/quick-estimates", headers=admin_headers).json()]
    assert "Listed portal" in names


def test_every_mapped_component_exists_in_catalog(client: TestClient, admin_headers: H) -> None:
    cfg = quick_config()
    keys = {c["key"] for c in client.get("/catalog", headers=admin_headers).json()["components"]}
    mapped = {k for t in cfg.sizing.tiers for k in t.base_components}
    mapped |= {k for f in cfg.features for k in f.components}
    mapped |= {k for q in cfg.questions.values() for o in q.options for k in o.extra_components}
    assert mapped <= keys


def test_questions_ranked_by_price_impact(client: TestClient, admin_headers: H) -> None:
    body = {"name": "Impact", "features": ["online_forms", "ai_chatbot"], "choices": {}}
    r = client.post("/quick-estimate/impact", json=body, headers=admin_headers)
    assert r.status_code == 200, r.text
    ranked = r.json()
    impacts = [q["impact_paise"] for q in ranked]
    assert impacts == sorted(impacts, reverse=True) and impacts[0] > 0
    scale = next(q for q in ranked if q["key"] == "scale")
    prices = [o["likely_paise"] for o in scale["options"] if o["value"] != "not_sure"]
    assert prices == sorted(prices)  # more users cost more
    # nothing was saved
    assert all(
        s["name"] != "Impact" for s in client.get("/quick-estimates", headers=admin_headers).json()
    )
    with_years = client.post(
        "/quick-estimate/impact", json={**body, "overrides": {"om_years": 4}}, headers=admin_headers
    ).json()
    assert "support_years" not in {q["key"] for q in with_years}


def test_custom_features_are_priced(client: TestClient, admin_headers: H) -> None:
    """Features outside the ready-made list (typed in by the user) still get priced."""
    base = quick(client, admin_headers, features=["online_forms"]).json()
    extra = [
        {"name": "Vehicle tracking with GIS map", "category": "module", "size": "L"},
        {"name": "Android app for inspectors", "category": "mobile", "size": "M"},
    ]
    s = quick(client, admin_headers, features=["online_forms"], custom_features=extra).json()
    assert s["planned_paise"] > base["planned_paise"]
    assert "Vehicle tracking with GIS map" in s["features"]
    detail = client.get(f"/estimates/{s['estimate_id']}", headers=admin_headers).json()
    labels = {ln["label"] for ln in detail["lines"]}
    assert {"Vehicle tracking with GIS map", "Android app for inspectors"} <= labels
    line = next(ln for ln in detail["lines"] if ln["label"] == "Android app for inspectors")
    trace = client.get(
        f"/estimates/{s['estimate_id']}/lines/{line['id']}/trace", headers=admin_headers
    ).json()["trace"]
    assert trace["component"]["catalog_key"] == "custom_mobile_app"
    assert trace["requirements"][0]["clause_ref"] == "Added by user: Android app for inspectors"
    only_custom = quick(client, admin_headers, features=[], custom_features=extra[:1])
    assert only_custom.status_code == 201


def test_options_list_custom_feature_types(client: TestClient, admin_headers: H) -> None:
    body = client.get("/quick-estimate/options", headers=admin_headers).json()
    assert {t["key"] for t in body["custom_feature_types"]} == {
        "module",
        "integration",
        "report",
        "ai",
        "mobile",
    }


def test_traditional_vs_ai_era_price(client: TestClient, admin_headers: H) -> None:
    """Every estimate also prices the same scope as if built without AI tools."""
    s = quick(client, admin_headers, features=["online_forms", "approval_workflow"]).json()
    assert s["traditional_paise"] > s["likely_paise"]
    assert s["traditional_build_only_paise"] > s["build_only_paise"]
    assert 0 < s["ai_saving_percent"] < 100


def test_client_paid_costs_listed_separately(client: TestClient, admin_headers: H) -> None:
    features = ["online_forms", "payments", "notifications"]
    theirs = quick(client, admin_headers, features=features, choices={"hosting": "existing"}).json()
    ours = quick(client, admin_headers, features=features).json()  # public cloud, in the cost
    paid = {c["key"]: c for c in theirs["client_pays"]}
    assert paid["hosting"]["first_year_paise"] > 0
    assert paid["hosting"]["total_paise"] >= paid["hosting"]["first_year_paise"]
    assert "2%" in paid["payment_gateway"]["note"]
    assert "sms" in paid  # service fees are paid to the providers, listed with amounts
    assert "hosting" not in {c["key"] for c in ours["client_pays"]}
    assert ours["likely_paise"] > theirs["likely_paise"]
    detail = client.get(f"/estimates/{theirs['estimate_id']}", headers=admin_headers).json()
    assert any(ln["bucket"] == "build.tools" for ln in detail["lines"])


def test_price_follows_what_is_built_not_who_orders_it(
    client: TestClient, admin_headers: H
) -> None:
    """No client-type question: the same features at the same level cost the same for anyone;
    a lean project costs less because it builds less."""
    opts = client.get("/quick-estimate/options", headers=admin_headers).json()
    keys = {q["key"] for q in opts["questions"]}
    assert not keys & {"buyer", "project_size", "hosting_scope", "usage_scope"}
    assert {"version", "hosting", "security_audit", "reporting"} <= keys
    hosting = next(q for q in opts["questions"] if q["key"] == "hosting")
    assert hosting["label"] == "Where will it run?"
    assert "existing" in {o["value"] for o in hosting["options"]}
    features = ["inventory", "search", "dashboards"]
    basic = quick(
        client, admin_headers, features=features,
        feature_levels={"inventory": "basic", "dashboards": "basic"},
    ).json()  # fmt: skip
    advanced = quick(
        client, admin_headers, features=features,
        feature_levels={"inventory": "advanced", "dashboards": "advanced"},
        choices={"security_audit": "yes", "reporting": "yes"},
    ).json()  # fmt: skip
    assert basic["build_only_paise"] * 2 < advanced["build_only_paise"]  # same users, more work
    assert basic["high_paise"] - basic["low_paise"] > basic["likely_paise"] // 5  # honest range
    assert basic["should_cost"] and "hours each feature takes" in basic["accuracy_note"]
    assert basic["market"]["projects"] > 0  # real contracts of this size, for comparison


def test_ai_usage_shown_apart_from_support(client: TestClient, admin_headers: H) -> None:
    options = client.get("/quick-estimate/options", headers=admin_headers).json()
    chatbot = next(q for q in options["questions"] if q["key"] == "chatbot_task")
    assert chatbot["only_with_features"] == ["ai_chatbot"] and chatbot["group"] == "detail"
    s = quick(client, admin_headers, choices={"chatbot_task": "advanced"}).json()
    parts = {p["key"]: p for p in s["parts"]}
    assert parts["ai_usage"]["amount_paise"] > 0
    assert sum(p["amount_paise"] for p in s["parts"]) == s["planned_paise"]
    simple = quick(client, admin_headers, choices={"chatbot_task": "simple"}).json()
    simple_ai = next(p for p in simple["parts"] if p["key"] == "ai_usage")["amount_paise"]
    assert simple_ai * 10 < parts["ai_usage"]["amount_paise"]
    no_ai = quick(client, admin_headers, features=["online_forms"]).json()
    assert "ai_usage" not in {p["key"] for p in no_ai["parts"]}


def test_cost_items_explain_the_whole_price(client: TestClient, admin_headers: H) -> None:
    s = quick(
        client,
        admin_headers,
        features=["online_forms", "payments", "maps", "notifications", "ai_chatbot"],
        choices={"platforms": "web_mobile", "scale": "up_to_1l"},
    ).json()
    items = {i["key"]: i for i in s["cost_items"]}
    assert sum(i["amount_paise"] for i in s["cost_items"]) == s["planned_paise"]
    assert "other" not in items  # every cost line has a plain item
    assert items["ai_coding"]["amount_paise"] > 0 and items["dev_tools"]["amount_paise"] > 0
    assert items["team_build"]["person_days"] > 0
    assert items["tax"]["group_label"] == "Margin, risk buffer and tax"
    # every item also says what it would cost without AI tools
    assert items["team_build"]["traditional_paise"] > items["team_build"]["amount_paise"]
    assert items["ai_coding"]["traditional_paise"] == 0  # no AI subscriptions without AI
    assert items["ai_review"]["person_days"] > 0  # people check what the AI wrote
    assert items["ai_review"]["traditional_paise"] == 0
    assert {"sms", "maps", "apple_developer"} <= {c["key"] for c in s["client_pays"]}


def test_cost_items_hide_margin_from_viewers(
    client: TestClient, admin_headers: H, viewer_headers: H
) -> None:
    s = quick(client, admin_headers).json()
    assert "margin" in {i["key"] for i in s["cost_items"]}
    seen = client.get(f"/estimates/{s['estimate_id']}/summary", headers=viewer_headers).json()
    assert "margin" not in {i["key"] for i in seen["cost_items"]}
    assert sum(i["amount_paise"] for i in seen["cost_items"]) == s["planned_paise"]


def test_small_add_on_does_not_resize_the_project(client: TestClient, admin_headers: H) -> None:
    eight = ["documents", "dashboards", "ai_chatbot", "payments", "billing", "bookings"]
    eight += ["mobile_app", "maps"]
    base = quick(client, admin_headers, features=eight).json()
    more = quick(client, admin_headers, features=[*eight, "notifications"]).json()
    assert base["project_size"] == more["project_size"] and base["size_points"] == 16
    assert base["planned_paise"] < more["planned_paise"] < base["planned_paise"] * 1.15


def test_no_support_hands_running_costs_to_the_client(client: TestClient, admin_headers: H) -> None:
    s = quick(
        client, admin_headers, features=["online_forms", "ai_chatbot", "maps"],
        choices={"support_years": 0},
    ).json()  # fmt: skip
    detail = client.get(f"/estimates/{s['estimate_id']}", headers=admin_headers).json()
    assert not [ln for ln in detail["lines"] if ln["year"] > 0]  # nothing after launch in the price
    run = next(p for p in s["parts"] if p["key"] == "run")
    assert run["amount_paise"] == 0 and run["label"].startswith("No support")
    paid = {c["key"]: c for c in s["client_pays"]}
    assert paid["hosting"]["first_year_paise"] > 0  # the client must budget running costs
    assert paid["llm_api"]["label"] == "AI chatbot usage"
    assert "services.maps" not in {i["key"] for i in s["cost_items"]}


def test_launch_extras_can_be_switched_on_or_off(client: TestClient, admin_headers: H) -> None:
    def buckets(choices: dict[str, str]) -> set[str]:
        s = quick(client, admin_headers, choices=choices).json()
        detail = client.get(f"/estimates/{s['estimate_id']}", headers=admin_headers).json()
        return {ln["bucket"] for ln in detail["lines"] if ln["likely_paise"] > 0}

    usual = buckets({})
    assert {"go_live.training", "go_live.hypercare"} <= usual
    assert not {"go_live.security_audit", "programme.steering_meetings"} & usual  # only if asked
    extras = buckets({"security_audit": "yes", "reporting": "yes"})
    assert {"go_live.security_audit", "programme.steering_meetings"} <= extras
    off = buckets({"launch_help": "none"})
    assert not {"go_live.training", "go_live.hypercare"} & off


def test_questions_hide_when_support_is_off(client: TestClient, admin_headers: H) -> None:
    opts = client.get("/quick-estimate/options", headers=admin_headers).json()
    q = {x["key"]: x for x in opts["questions"]}
    assert q["helpdesk_scope"]["hide_when"] == {"support_years": [0]}
    assert 0 in [o["value"] for o in q["support_years"]["options"]]


def test_every_figure_comes_with_a_range(client: TestClient, admin_headers: H) -> None:
    s = quick(client, admin_headers, features=["online_forms", "maps", "ai_chatbot"]).json()
    assert s["build_only_low_paise"] < s["build_only_paise"] < s["build_only_high_paise"]
    for part in s["parts"]:
        assert part["low_paise"] <= part["amount_paise"] <= part["high_paise"], part["key"]
    for item in s["cost_items"]:
        assert item["low_paise"] <= item["amount_paise"] <= item["high_paise"], item["key"]
        if item["person_days"]:
            assert item["person_days_low"] <= item["person_days"] <= item["person_days_high"]
    for paid in s["client_pays"]:
        if paid["first_year_paise"] is not None:
            low, high = paid["first_year_low_paise"], paid["first_year_high_paise"]
            assert low <= paid["first_year_paise"] <= high, paid["key"]
    pdf = client.get(f"/estimates/{s['estimate_id']}/report.pdf", headers=admin_headers)
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")


def test_feature_levels_drive_the_price(client: TestClient, admin_headers: H) -> None:
    features = ["online_forms", "approval_workflow", "documents", "dashboards"]

    def price(level: str) -> dict[str, Any]:
        out: dict[str, Any] = quick(
            client, admin_headers, features=features,
            feature_levels=dict.fromkeys(features, level),
        ).json()  # fmt: skip
        return out

    basic, standard, advanced = price("basic"), price("standard"), price("advanced")
    assert basic["likely_paise"] < standard["likely_paise"] < advanced["likely_paise"]
    assert (basic["project_size"], basic["size_points"]) == ("Small", 4)
    assert (advanced["project_size"], advanced["size_points"]) == ("Medium", 16)
    assert basic["market"]["project_size"] == "Small"
    detail = client.get(f"/estimates/{basic['estimate_id']}", headers=admin_headers).json()
    basic_buckets = {ln["bucket"] for ln in detail["lines"]}
    assert "programme.steering_meetings" not in basic_buckets  # delivered lean
    assert "go_live.security_audit" not in basic_buckets
    levels = {f["key"]: f["levels"] for f in client.get(
        "/quick-estimate/options", headers=admin_headers
    ).json()["features"]}  # fmt: skip
    assert [lv["key"] for lv in levels["online_forms"]] == ["basic", "standard", "advanced"]
    assert levels["online_forms"][0]["hint"] == "One or two simple forms"
    assert levels["notifications"] == []  # one size only
    stray = quick(client, admin_headers, feature_levels={"maps": "basic"})
    assert stray.status_code == 422  # a level for a feature that is not ticked


def test_cost_by_feature_with_and_without_ai(client: TestClient, admin_headers: H) -> None:
    s = quick(
        client, admin_headers, features=["online_forms", "documents", "search"],
        feature_levels={"online_forms": "advanced"},
    ).json()  # fmt: skip
    costs = {c["label"]: c for c in s["feature_costs"]}
    forms = costs["Online application or registration forms"]
    assert forms["level"] == "Advanced"
    assert forms["traditional_paise"] > forms["amount_paise"] > 0  # AI tools save effort
    assert costs["Search"]["level"] is None  # one size only
    assert list(costs)[-1].startswith("Standard building blocks")
    detail = client.get(f"/estimates/{s['estimate_id']}", headers=admin_headers).json()
    component_total = sum(
        ln["likely_paise"] for ln in detail["lines"] if ln["component_instance_id"]
    )
    assert sum(c["amount_paise"] for c in s["feature_costs"]) == component_total


def test_delete_estimate_and_project(client: TestClient, admin_headers: H) -> None:
    s = quick(client, admin_headers).json()
    est, project = s["estimate_id"], s["project_id"]
    viewer_cannot = client.delete(f"/projects/{project}", headers={})
    assert viewer_cannot.status_code == 401
    assert client.delete(f"/estimates/{est}", headers=admin_headers).status_code == 204
    assert client.get(f"/estimates/{est}", headers=admin_headers).status_code == 404
    assert client.get(f"/projects/{project}", headers=admin_headers).status_code == 200
    assert client.delete(f"/projects/{project}", headers=admin_headers).status_code == 204
    assert client.get(f"/projects/{project}", headers=admin_headers).status_code == 404
    listed = client.get("/quick-estimates", headers=admin_headers).json()
    assert project not in {x["project_id"] for x in listed}


def test_templates_save_reuse_and_delete(client: TestClient, admin_headers: H) -> None:
    s = quick(
        client, admin_headers, name="Library system",
        features=["inventory", "search"], feature_levels={"inventory": "basic"},
    ).json()  # fmt: skip
    r = client.post(
        "/templates", json={"project_id": s["project_id"], "name": "Library starter"},
        headers=admin_headers,
    )  # fmt: skip
    assert r.status_code == 201, r.text
    t = r.json()
    assert t["features"] == ["inventory", "search"]
    assert t["request"]["feature_levels"] == {"inventory": "basic"}
    assert t["id"] in {x["id"] for x in client.get("/templates", headers=admin_headers).json()}
    # a new estimate from the template gives the same price
    again = client.post("/quick-estimates", json=t["request"], headers=admin_headers).json()
    assert again["planned_paise"] == s["planned_paise"]
    assert client.delete(f"/templates/{t['id']}", headers=admin_headers).status_code == 204
    assert client.get(f"/templates/{t['id']}", headers=admin_headers).status_code == 404


def test_ready_made_product_costs_far_less(client: TestClient, admin_headers: H) -> None:
    features = ["ai_chatbot", "grievances"]
    custom = quick(client, admin_headers, features=features).json()
    ready = quick(
        client, admin_headers, features=features, choices={"build_type": "ready_product"}
    ).json()
    assert ready["build_only_paise"] * 2 < custom["build_only_paise"]
    assert "not from what vendors charged" in custom["accuracy_note"]  # should-cost


def test_similar_real_projects_are_shown(client: TestClient, admin_headers: H) -> None:
    s = quick(
        client, admin_headers, features=["mobile_app", "payments", "bookings"],
        feature_levels={"mobile_app": "basic", "payments": "basic", "bookings": "basic"},
    ).json()  # fmt: skip
    similar = s["similar_projects"]
    assert 1 <= len(similar) <= 5
    scores = [p["match_percent"] for p in similar]
    assert scores == sorted(scores, reverse=True)
    assert all(p["high_paise"] >= p["low_paise"] and p["source_url"] for p in similar)
    assert similar[0]["size"] == "small"


def test_client_mode_gives_a_bid_check_at_market_rates(
    client: TestClient, admin_headers: H
) -> None:
    assert (
        client.put("/settings", json={"margin_percent": "0.5"}, headers=admin_headers).status_code
        == 200
    )
    vendor = quick(client, admin_headers).json()
    buyer = quick(client, admin_headers, mode="client").json()
    assert vendor["mode"] == "vendor" and vendor["bid_check"] is None
    check = buyer["bid_check"]
    assert buyer["mode"] == "client"
    assert check["too_low_below_paise"] < check["fair_low_paise"] < check["fair_high_paise"]
    assert check["fair_high_paise"] < check["too_high_above_paise"]
    assert buyer["planned_paise"] < vendor["planned_paise"]  # market margin, not our 50%
    client.put("/settings", json={}, headers=admin_headers)


def test_team_needed_by_role(client: TestClient, admin_headers: H) -> None:
    """The people behind the work, by role: from the engine's person-days, with and without AI."""
    s = quick(client, admin_headers, features=["online_forms", "ai_chatbot", "mobile_app"]).json()
    team = {r["role"]: r for r in s["team"]}
    dev = team["role.developer"]
    assert dev["label"] == "Developer" and float(dev["people"]) > 0
    assert float(dev["traditional_people"]) >= float(dev["people"])  # AI tools: fewer people
    assert "role.ml_engineer" in team  # the chatbot needs an AI engineer
    total = sum(float(r["people"]) for r in s["team"])
    assert abs(float(s["team_people"]) - total) < 0.01
    months = float(s["build_months"])
    assert abs(float(dev["person_months"]) - float(dev["people"]) * months) < 0.2
    assert s["support_team"] and all(float(r["person_months"]) > 0 for r in s["support_team"])
    assert s["traditional_build_months"] is not None


def test_questions_add_features_and_set_levels(client: TestClient, admin_headers: H) -> None:
    """Answers stand in for tick boxes: a mobile app, other software, old data; MVP / full."""
    base = {"features": ["bookings", "payments"]}
    web = quick(client, admin_headers, **base).json()
    app = quick(client, admin_headers, **base, choices={"platforms": "web_mobile"}).json()
    assert "Mobile app (Android / iOS)" in app["features"]
    assert app["build_only_paise"] > web["build_only_paise"]
    linked = quick(
        client, admin_headers, **base, choices={"integrations": "many", "old_data": "lot"}
    ).json()
    levels = {c["label"]: c["level"] for c in linked["feature_costs"]}
    assert levels["Connect to existing systems (SAP, old software)"] == "Advanced"
    assert levels["Move data from the old system"] == "Advanced"
    mvp = quick(client, admin_headers, **base, choices={"version": "mvp"}).json()
    assert {c["level"] for c in mvp["feature_costs"] if c["level"]} == {"Basic"}
    assert mvp["build_only_paise"] < web["build_only_paise"]
    # a level chosen for one feature still wins over the MVP default
    mixed = quick(
        client, admin_headers, **base, choices={"version": "mvp"},
        feature_levels={"payments": "advanced"},
    ).json()  # fmt: skip
    assert {c["label"]: c["level"] for c in mixed["feature_costs"]}["Online fee payment"] == (
        "Advanced"
    )
    ready = quick(client, admin_headers, **base, choices={"design": "ready"}).json()
    assert ready["build_only_paise"] < web["build_only_paise"]


def test_not_sure_prices_the_usual_answer_with_a_wider_range(
    client: TestClient, admin_headers: H
) -> None:
    sure = quick(client, admin_headers).json()
    unsure = quick(
        client, admin_headers,
        choices={"scale": "not_sure", "build_type": "not_sure", "hosting": "not_sure"},
    ).json()  # fmt: skip

    def width(s: dict[str, Any]) -> float:
        return float(s["high_paise"] - s["low_paise"]) / float(s["likely_paise"])

    def buffer_share(s: dict[str, Any]) -> float:
        items = {i["key"]: i for i in s["cost_items"]}
        return float(items["buffer"]["amount_paise"]) / float(s["planned_paise"])

    # vaguer requirements: a bigger risk buffer (deterministic) and a range at least as wide
    # (the simulation's own noise is a few percent, as each estimate draws its own seed)
    assert buffer_share(unsure) > buffer_share(sure)
    assert width(unsure) > 0.95 * width(sure)
    assert unsure["not_sure"] == [
        "How many people will use it?",
        "Should it be built from scratch, or set up on a ready-made product?",
        "Where will it run?",
    ]
    assert sure["not_sure"] == []


def test_first_screen_kinds_of_software(client: TestClient, admin_headers: H) -> None:
    """The kind of software only orders and pre-ticks features; it never changes the price."""
    opts = client.get("/quick-estimate/options", headers=admin_headers).json()
    types = {t["key"]: t for t in opts["project_types"]}
    assert {"portal", "business", "store", "booking", "ai", "other"} == set(types)
    keys = {f["key"] for f in opts["features"] if not f["hidden"]}
    for t in types.values():
        assert set(t["features"]) <= keys and set(t["suggested"]) <= set(t["features"])
    assert types["other"]["features"] == []  # every feature
    same = {"features": ["bookings", "payments"]}
    booking = quick(client, admin_headers, **same, project_type="booking").json()
    store = quick(client, admin_headers, **same, project_type="store").json()
    assert booking["planned_paise"] == store["planned_paise"]
    assert quick(client, admin_headers, **same, project_type="rocket").status_code == 422

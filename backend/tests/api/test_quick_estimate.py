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
    assert scale["default"] == "up_to_10k" and len(scale["options"]) == 11
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
    # the shared range for the project's size first, then its own biggest unknown (v23+)
    assert "the biggest unknown is" in s["biggest_uncertainty"].lower()
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


def test_too_short_deadline_is_priced_at_the_fastest(client: TestClient, admin_headers: H) -> None:
    """A deadline too short to build in, even with a bigger team, is priced at the fastest
    possible time and the summary says so (OPEN_QUESTIONS 179); the form shows both times."""
    features = ["online_forms", "approval_workflow", "documents", "dashboards", "payments", "crm"]
    body = {
        "features": features, "choices": {"scale": "over_10l"},
        "feature_levels": dict.fromkeys(features, "advanced"),
    }  # fmt: skip
    plan = client.post(
        "/quick-estimate/schedule", json={"name": "x", **body}, headers=admin_headers
    ).json()
    usual, fastest = float(plan["usual_months"]), float(plan["fastest_months"])
    assert 1 < fastest < usual

    s = quick(client, admin_headers, deadline_months=1, **body).json()
    assert s["feasible"] and s["likely_paise"]
    assert float(s["deadline_asked_months"]) == 1
    assert float(s["deadline_priced_months"]) == fastest
    assert float(s["build_months"]) == fastest
    at_fastest = quick(client, admin_headers, deadline_months=fastest, **body).json()
    assert at_fastest["deadline_priced_months"] is None  # priced as asked
    assert at_fastest["likely_paise"] > quick(client, admin_headers, **body).json()["likely_paise"]


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


def test_impact_with_a_level_for_a_feature_an_answer_adds(
    client: TestClient, admin_headers: H
) -> None:
    """A level for the connection "other software" adds: the "No" answer drops the connection,
    and its level with it (the review form of the RailTel document failed here, 2026-10-27)."""
    body = {
        "name": "Impact",
        "features": ["online_forms"],
        "choices": {"integrations": "one_two"},
        "feature_levels": {"connect_existing": "basic"},
    }
    r = client.post("/quick-estimate/impact", json=body, headers=admin_headers)
    assert r.status_code == 200, r.text
    integrations = next(q for q in r.json() if q["key"] == "integrations")
    assert all(o["likely_paise"] for o in integrations["options"])


def test_deadline_in_weeks_is_priced_as_part_months(client: TestClient, admin_headers: H) -> None:
    """The form asks weeks and sends months to two decimals (12 weeks = 2.77 months)."""
    s = quick(client, admin_headers, features=["online_forms"], deadline_months=2.77)
    assert s.status_code == 201, s.text
    assert (
        quick(client, admin_headers, features=["online_forms"], deadline_months=0).status_code
        == 422
    )


def test_every_question_has_a_topic(client: TestClient, admin_headers: H) -> None:
    """The form asks one topic at a time, in the order of `topics` (OPEN_QUESTIONS 177)."""
    options = client.get("/quick-estimate/options", headers=admin_headers).json()
    topics = [t["key"] for t in options["topics"]]
    assert topics == ["build", "users", "hosting", "support", "contract"]
    assert all(q["topic"] in topics for q in options["questions"])


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
    """Every estimate also prices the same scope as if built without AI tools. Parameters v18:
    effort data of unknown era counts as pre-AI (the hours were calibrated on pre-AI
    projects), so the AI saving is taken off it and the estimate is below the traditional
    price."""
    s = quick(client, admin_headers, features=["online_forms", "approval_workflow"]).json()
    assert s["traditional_paise"] > 0 and s["traditional_build_only_paise"] > 0
    assert s["ai_saving_percent"] > 1  # unknown era counts as pre-AI (v18)
    assert s["era_sensitivity"] is None  # nothing left to show: unknown is priced as pre-AI


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
    assert basic["market"] is None  # market prices are not shown (show_market_prices off)


def test_no_market_prices_are_shown(client: TestClient, admin_headers: H) -> None:
    """Market prices fluctuate too much to check an estimate against (show_market_prices off):
    no market box and no similar contracts, and the note says the price comes from hours."""
    small = quick(client, admin_headers, features=["online_forms"]).json()
    assert small["market"] is None and small["similar_projects"] == []
    assert "not from what vendors charged" in small["accuracy_note"]
    assert (
        "not yet been checked against what finished projects really cost"
        in (small["accuracy_note"])
    )
    # the production-path back-test, with who read the tenders (OPEN_QUESTIONS 161)
    assert "8 real government tenders" in small["accuracy_note"]
    assert "stand-in AI model" in small["accuracy_note"]
    assert "3 of the 8 published prices" in small["accuracy_note"]


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
    # every item also says what it would cost without AI tools (the same for the team on
    # catalog v6 when no block's effort data is pre-AI: no saving is taken off unknown-era data)
    assert items["team_build"]["traditional_paise"] >= items["team_build"]["amount_paise"]
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
    # unknown-era effort data counts as pre-AI (parameters v18): the AI saving is taken off
    assert forms["traditional_paise"] > forms["amount_paise"] > 0
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


def test_similar_real_projects_are_not_shown(client: TestClient, admin_headers: H) -> None:
    s = quick(
        client, admin_headers, features=["mobile_app", "payments", "bookings"],
        feature_levels={"mobile_app": "basic", "payments": "basic", "bookings": "basic"},
    ).json()  # fmt: skip
    assert s["similar_projects"] == []  # show_market_prices off


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
    months, people = float(s["build_months"]), float(dev["people"])
    # each of the three is rounded to 0.1 on its own, so their product may be off by that much
    rounding = 0.05 * months + 0.05 * people + 0.05 + 0.01
    assert abs(float(dev["person_months"]) - people * months) < rounding
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

    def upside(s: dict[str, Any]) -> float:
        """How far the items' own pessimistic values sit above the plan (deterministic)."""
        t = client.get(f"/estimates/{s['estimate_id']}", headers=admin_headers).json()["totals"]
        return float(t["high_sum_paise"] - t["likely_paise"]) / float(t["likely_paise"])

    # vaguer requirements: wider item spreads (deterministic; parameter set v16 has no fixed
    # contingency, the simulation carries the risk) and a range at least as wide (the
    # simulation's own noise is a few percent, as each estimate draws its own seed)
    assert upside(unsure) > upside(sure)
    assert width(unsure) > 0.95 * width(sure)
    assert unsure["not_sure"] == [
        "How many people will use it?",
        "How will it be built?",
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


def test_scope_items_priced_and_shown(client: TestClient, admin_headers: H) -> None:
    """What else a feature needs: offered with the options, priced only when chosen, shown as
    its own building cost when it adds a block, and listed in the summary."""
    options = client.get("/quick-estimate/options", headers=admin_headers).json()
    groups = {g["key"]: g for g in options["scope"]}
    assert groups["sign_in"]["feature"] is None  # every project
    assert groups["forms_scope"]["feature"] == "online_forms"
    items = {i["key"]: i for g in options["scope"] for i in g["items"]}
    assert all(i["hint"] for i in items.values())  # plain words for every extra on the form
    assert items["enterprise_sso"]["advanced"] and not items["otp_codes"]["advanced"]
    assert items["enterprise_sso"]["ask"] != items["enterprise_sso"]["label"]
    base = quick(client, admin_headers, features=["online_forms"]).json()
    more = quick(
        client, admin_headers, features=["online_forms"], scope=["enterprise_sso", "forms_ekyc"]
    ).json()
    assert base["scope"] == [] and len(more["scope"]) == 2
    assert more["market"] == base["market"]  # published prices: scope never moves them
    assert more["build_only_paise"] > base["build_only_paise"]
    costs = {c["label"]: c for c in more["feature_costs"]}
    sso = next(v for k, v in costs.items() if k.startswith("Sign-in and user accounts: Single"))
    assert sso["amount_paise"] > 0
    form = costs["Online application or registration forms"]
    before = {c["label"]: c for c in base["feature_costs"]}[
        "Online application or registration forms"
    ]["amount_paise"]
    # the feature itself costs about the same; the item is its own row (parameters v20+: the
    # review cap is a share of the whole build, so more blocks can loosen it a little)
    assert abs(form["amount_paise"] - before) <= before * 0.05
    assert sum(c["amount_paise"] for c in more["feature_costs"]) > sum(
        c["amount_paise"] for c in base["feature_costs"]
    )
    items = {i["key"]: i for i in more["scope_items"]}
    assert items["enterprise_sso"]["amount_paise"] == sso["amount_paise"] > 0
    assert items["forms_ekyc"]["amount_paise"] > 0 and items["enterprise_sso"]["note"]
    # an item whose block is already in the project adds nothing, and says so (0)
    paid = quick(client, admin_headers, features=["online_forms", "payments"], scope=["forms_fee"])
    assert {i["key"]: i["amount_paise"] for i in paid.json()["scope_items"]} == {"forms_fee": 0}
    bad = quick(client, admin_headers, features=["online_forms"], scope=["booking_payment"])
    assert bad.status_code == 422  # bookings not ticked


def test_typed_description_suggests_scope(client: TestClient, admin_headers: H) -> None:
    text = (
        "A portal where vendors apply online with their documents. "
        "Staff must use two-factor authentication to sign in."
    )
    r = client.post("/quick-estimate/suggest", json={"text": text}, headers=admin_headers)
    assert r.status_code == 200, r.text
    scope = {s["key"]: s for s in r.json()["scope"]}
    assert "two_step_sign_in" in scope
    assert "two-factor authentication" in scope["two_step_sign_in"]["quote"]


def test_ai_saving_passed_to_the_client_is_a_company_setting(
    client: TestClient, admin_headers: H
) -> None:
    """A company setting (OPEN_QUESTIONS 173), not a question on the form; the cost model is the
    same, the share not passed on is kept as margin and shown as "AI saving identified"."""
    options = client.get("/quick-estimate/options", headers=admin_headers).json()
    assert "ai_passthrough" not in {q["key"] for q in options["questions"]}
    keep = client.put("/settings", json={"ai_passthrough": "keep"}, headers=admin_headers)
    assert keep.is_success
    try:
        by_setting = quick(client, admin_headers).json()
        assert by_setting["ai_saving"]["passed_percent"] == 0
    finally:
        client.put("/settings", json={}, headers=admin_headers)
    passed = quick(client, admin_headers, choices={"ai_passthrough": "all"}).json()
    kept = quick(client, admin_headers, choices={"ai_passthrough": "keep"}).json()
    assert passed["ai_saving"]["passed_percent"] == 100 and kept["ai_saving"]["passed_percent"] == 0
    saving = passed["ai_saving"]["identified_paise"]
    assert saving > 0 and kept["ai_saving"]["identified_paise"] == saving
    assert 0 < passed["ai_saving"]["percent"] < 100
    assert kept["likely_paise"] > passed["likely_paise"]
    assert kept["build_only_paise"] == passed["build_only_paise"]  # costs unchanged


def test_ai_saving_kept_is_its_own_internal_item(
    client: TestClient, admin_headers: H, viewer_headers: H
) -> None:
    """Kept AI saving shown apart from the profit margin (the estimator's discount room), and
    only to people who may see margin."""
    kept = quick(client, admin_headers, choices={"ai_passthrough": "keep"}).json()
    assert kept["ai_saving"]["kept_paise"] > 0
    items = {i["key"]: i for i in kept["cost_items"]}
    assert items["ai_saving_kept"]["amount_paise"] == kept["ai_saving"]["kept_paise"]
    seen = client.get(f"/estimates/{kept['estimate_id']}/summary", headers=viewer_headers).json()
    assert seen["ai_saving"]["kept_paise"] is None
    assert "ai_saving_kept" not in {i["key"] for i in seen["cost_items"]}


def test_users_price_smoothly(client: TestClient, admin_headers: H) -> None:
    """A typed user count is priced as typed, and the people online at once and the chatbot's
    questions follow it on the users curve, not the top of its band (OPEN_QUESTIONS 182)."""
    body = quick(client, admin_headers, choices={"scale": "up_to_25k"}).json()
    assert (body["users_total"], body["peak_online"]) == (25000, 333)  # the band's top
    prices = []
    for users in (10_000, 15_000, 25_000):
        r = quick(
            client,
            admin_headers,
            choices={"scale": "up_to_25k" if users > 10_000 else "up_to_10k"},
            overrides={"users_total": users},
        )
        assert r.status_code == 201, r.text
        prices.append(r.json()["likely_paise"])
    s = r.json()
    assert (s["users_total"], s["peak_online"]) == (25000, 333)
    assert prices[0] < prices[1] < prices[2]
    typed = quick(
        client, admin_headers, choices={"scale": "up_to_25k"}, overrides={"users_total": 15000}
    ).json()
    assert (typed["users_total"], typed["peak_online"]) == (15000, 244)
    # a stated number of people online wins over the curve
    own = quick(
        client,
        admin_headers,
        choices={"scale": "up_to_25k"},
        overrides={"users_total": 15000, "peak_concurrent_users": 900},
    ).json()
    assert own["peak_online"] == 900

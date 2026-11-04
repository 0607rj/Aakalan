"""Industry, project type, user roles and prerequisite warnings (OPEN_QUESTIONS 205): shown
only. They never change a price or a seed, and readings made before the industry field load."""

import json
from pathlib import Path

from app.services.extraction.tender import TenderExtraction
from app.services.quick.config import quick_config
from app.services.quick.context import missing_prerequisites, project_type, user_roles
from app.services.quick.service import QuickRequest, request_seed

CFG = quick_config()
READINGS = Path(__file__).parents[1] / "fixtures" / "readings_v10"


def test_roles_come_from_the_stories_each_once() -> None:
    stories = [
        "As a patient, I can book an appointment.",
        "As a Patient, I can pay online.",
        "As an administrator, I can see collections.",
        "As the clinic manager, I can add doctors.",
        "Patients get a reminder.",  # not a story: no role
    ]
    assert user_roles(stories, 8) == ["Patient", "Administrator", "Clinic manager"]
    assert user_roles(stories, 2) == ["Patient", "Administrator"]


def test_the_type_is_the_project_type_sharing_most_features() -> None:
    store = next(t for t in CFG.project_types if t.key == "store").label
    booking = next(t for t in CFG.project_types if t.key == "booking").label
    assert project_type(CFG, ["online_store", "payments", "search"]) == store
    rules = CFG.project_context
    assert rules is not None
    assert project_type(CFG, ["bookings", "mobile_app"]) == f"{booking}, {rules.mobile_app_note}"
    assert project_type(CFG, ["old_data"]) == rules.other_type


def test_prerequisites_warn_but_add_nothing() -> None:
    warned = missing_prerequisites(CFG, ["marketplace"])
    assert [w.key for w in warned] == ["marketplace"]
    assert missing_prerequisites(CFG, ["marketplace", "payments"]) == []
    # the document asks for reminders, but bookings is not ticked
    stray = missing_prerequisites(CFG, ["payments"], ["booking_reminders", "booking_reminders"])
    assert [w.key for w in stray] == ["booking_reminders"]  # once
    assert stray[0].needs == ["Bookings / appointments"]
    assert missing_prerequisites(CFG, ["bookings"], ["booking_reminders"]) == []


def test_the_industry_never_changes_the_seed() -> None:
    plain = QuickRequest(name="x", features=["bookings"])
    with_domain = plain.model_copy(update={"project_domain": "Hospital care"})
    assert request_seed(plain, None) == request_seed(with_domain, None)


def test_readings_made_before_the_industry_field_still_load() -> None:
    for f in sorted(READINGS.glob("*.json")):
        saved = json.loads(f.read_text(encoding="utf-8"))["extraction"]
        assert "project_domain" not in saved
        reading = TenderExtraction.model_validate(saved)
        assert reading.project_domain == "" and reading.user_roles == []


def test_a_chosen_browser_only_build_gets_no_mobile_warning() -> None:
    """Offline entry and camera scanning in the browser (OPEN_QUESTIONS 206): no warning when
    the document or user answered "Website"; still one when the answer is only the default."""
    features = ["offline_app", "scanning"]
    assert {w.key for w in missing_prerequisites(CFG, features)} == set(features)
    assert missing_prerequisites(CFG, features, answered={"platforms": "web"}) == []
    # in-app purchases need an app store whatever the answer
    still = missing_prerequisites(CFG, ["app_purchases"], answered={"platforms": "web"})
    assert [w.key for w in still] == ["app_purchases"]

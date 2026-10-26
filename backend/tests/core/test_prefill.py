"""The review form's pre-fill (services/quick/prefill) and the production-path back-test that
prices it (OPEN_QUESTIONS 161)."""

import json
from datetime import date
from pathlib import Path

import pytest

from app.core.config import get_settings
from app.services.calibration.backtest import (
    AI_USE,
    NO_AI,
    backtest_production,
    load_benchmarks,
    load_readings,
    reading_request,
    reference_for,
)
from app.services.extraction.tender import TenderExtraction
from app.services.quick.config import quick_config
from app.services.quick.prefill import review_prefill
from app.services.seeding.reference import load_reference

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
READINGS = FIXTURES / "readings"
READINGS_V9 = FIXTURES / "readings_v9"  # + staff lines entered by hand (OPEN_QUESTIONS 162)
# What frontend/src/app/estimate/new/review.tsx sent for each saved reading, accepted untouched,
# recorded from the form itself before it used the backend pre-fill.
FORM = json.loads((FIXTURES / "review_form" / "requests.json").read_text(encoding="utf-8"))
# request fields the form does not send (the document id is the upload's own)
NOT_SENT = {"document_id", "deadline_months", "project_type"}
TYRE = "gem-cpcb-epr-waste-tyre-portal"
BATTERY = "gem-cpcb-epr-battery-portal"


def test_readings_are_tagged_with_their_reader() -> None:
    for folder in (READINGS, READINGS_V9):
        readings = load_readings(folder)
        assert len(readings) == 8
        for r in readings.values():
            assert "not the production" in r.reader_model.lower()
            assert r.read_on == date(2026, 10, 24)


def test_v9_readings_price_their_staff_lines() -> None:
    """OPEN_QUESTIONS 162: the hand-entered staff lines are priced as the staff list."""
    cfg = quick_config()
    for r in load_readings(READINGS_V9).values():
        assert "entered by hand" in r.reader_model and r.extraction.staff_lines
        form = review_prefill(cfg, r.extraction, "india")
        assert form.request.staff is not None and form.staff is not None
        assert "onsite_staff" not in form.request.overrides
        assert form.key_answers[0].key == "staff"


@pytest.mark.parametrize("benchmark_id", sorted(FORM["requests"]))
def test_prefill_matches_the_review_form(benchmark_id: str) -> None:
    reading = load_readings(READINGS)[benchmark_id]
    request = review_prefill(quick_config(), reading.extraction, "india").request
    sent = request.model_dump(mode="json", exclude=NOT_SENT)
    # a reading without staff lines sends no staff list (recorded before it existed)
    assert sent.pop("staff") is None
    # an upload sends no user stories (the form sends {}; recorded before they existed)
    assert sent.pop("feature_stories") == {}
    assert sent == FORM["requests"][benchmark_id]


def _extraction(**changes: object) -> TenderExtraction:
    base = load_readings(READINGS)[BATTERY].extraction
    return base.model_copy(update=changes)


def test_numbers_the_form_would_refuse_are_not_sent() -> None:
    ex = _extraction()
    numbers = dict(ex.numbers)
    numbers["om_years"] = numbers["om_years"].model_copy(update={"value": 40})  # above 10
    numbers["languages"] = numbers["om_years"].model_copy(update={"value": 2.5})  # not whole
    form = review_prefill(quick_config(), ex.model_copy(update={"numbers": numbers}), "india")
    assert "om_years" not in form.request.overrides
    assert "languages" not in form.request.overrides
    assert next(f for f in form.facts if f.key == "om_years").value == 40  # still shown


def test_a_found_app_answers_its_question_and_the_reading_wins() -> None:
    cfg = quick_config()
    ex = _extraction()
    form = review_prefill(cfg, ex, "india")
    assert form.choices["platforms"] == ex.choices["platforms"].value
    no_choice = ex.model_copy(update={"choices": {}})
    preset = review_prefill(cfg, no_choice, "india")
    # the mobile app it found is a question's answer, not a tick
    assert "mobile_app" not in preset.features
    assert preset.choices["platforms"] == "web_mobile"
    assert "platforms" in preset.answered


def test_production_path_back_test() -> None:
    settings = get_settings()
    cfg = quick_config()
    bench = load_benchmarks(settings.seeds_dir / "benchmarks" / "india.yaml")
    reference = reference_for(load_reference(settings.seeds_dir), "india")
    dials = reference["parameters"].calibration
    assert dials is not None
    readings = load_readings(READINGS)
    two = {k: readings[k] for k in (TYRE, BATTERY)}
    report = backtest_production(
        cfg,
        bench,
        reference,
        dials.effort_multiplier,
        dials.run_multiplier,
        two,
        as_of=date(2026, 10, 24),
    )
    assert report.path == "production"
    assert sorted(r.id for r in report.rows) == sorted(two)
    by_id = {r.id: r for r in report.rows}
    # the tyre tender's 3-month deadline cannot be met: priced without it, and said so
    assert by_id[TYRE].infeasible_deadline == 3
    assert by_id[BATTERY].infeasible_deadline is None
    assert all(r.estimate_pre_ai_minor and r.ratio_pre_ai for r in report.rows)
    # it prices the form's own request, with the back-test's AI use
    req = reading_request(cfg, readings[BATTERY], "india", NO_AI)
    assert req.choices[AI_USE] == NO_AI
    sent = req.model_dump(mode="json", exclude={*NOT_SENT, "staff", "feature_stories"})
    assert {**sent, "choices": {k: v for k, v in sent["choices"].items() if k != AI_USE}} == FORM[
        "requests"
    ][BATTERY]

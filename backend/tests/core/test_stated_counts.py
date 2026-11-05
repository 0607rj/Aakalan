"""Counts a document states for what is built (OPEN_QUESTIONS 194): real counts become modules,
citing the line; table item numbers and section numbers are never read as counts. After an AI
reading a count only sizes a feature the AI found, never adds one (OPEN_QUESTIONS 217)."""

import json
from pathlib import Path

from app.services.extraction.merge import apply_stated_counts
from app.services.extraction.stated_counts import find_stated_counts
from app.services.extraction.tender import FoundFeature, TenderExtraction
from app.services.quick.config import quick_config

CFG = quick_config()
RULES = CFG.stated_counts
assert RULES is not None
READING = (
    Path(__file__).parents[1] / "fixtures" / "readings_v10" / "gem-cpcb-epr-battery-portal.json"
)


def found(*lines: str) -> dict[str, int]:
    pages = [(1, "\n".join(lines))]
    hits = find_stated_counts(RULES, pages, "rfp.pdf", CFG.sizing.max_units)  # type: ignore[arg-type]
    return {k: v.count for k, v in hits.items()}


def empty() -> TenderExtraction:
    """A saved reading with no features (the battery tender states no counts)."""
    saved = json.loads(READING.read_text(encoding="utf-8"))
    return TenderExtraction.model_validate(saved["extraction"]).model_copy(update={"features": []})


def test_real_counts_are_read() -> None:
    assert found("Implementation of", "Phase - 4 UAT approval", "200 services") == {
        "online_forms": 200
    }
    assert found("4. API based integration with 20 State Systems") == {"connect_existing": 20}
    assert found("The portal will host 35 citizen services in phase one.") == {"online_forms": 35}
    # the largest count wins
    assert found("50 services", "100 more services", "200 services") == {"online_forms": 200}


def test_item_and_section_numbers_are_not_counts() -> None:
    assert found("69 Reports need to be customizable as per Bank's requirement.") == {}
    assert found("53 WhatsApp Banking Services Required:") == {}  # not an allowed word
    assert found("F1.36 services used by the customers. It") == {}  # a section number
    assert found("2 Integration of existing modules developed by CPCB") == {}
    assert found("2 Financial Proposal Forms") == {}
    assert found("8 Bid forms") == {}
    assert found("Integration with SMS gateway") == {}  # no count


def found_by_ai(*keys: str) -> TenderExtraction:
    """The saved AI reading with only these features found (one module each)."""
    features = [FoundFeature(key=k, label=CFG.feature(k).label, evidence=[]) for k in keys]
    return empty().model_copy(update={"features": features})


def test_a_count_makes_the_feature_several_modules_and_cites_the_line() -> None:
    reading = found_by_ai("online_forms", "connect_existing")
    apply_stated_counts(reading, [("rfp.pdf", [(3, "200 services\nintegration with 20 systems")])])
    by_key = {f.key: f for f in reading.features}
    forms, links = by_key["online_forms"], by_key["connect_existing"]
    assert (forms.story_units, forms.story_level) == (40, "standard")  # 200 / 5 a module
    assert (links.story_units, links.story_level) == (10, "standard")  # 20 / 2 a module
    assert forms.evidence[0].quote == "200 services" and forms.evidence[0].page == 3


def test_after_an_ai_reading_a_count_never_adds_a_feature() -> None:
    reading = empty()
    apply_stated_counts(reading, [("rfp.pdf", [(3, "200 services\nintegration with 20 systems")])])
    assert reading.features == []


def test_a_count_never_lowers_what_the_reading_found() -> None:
    reading = found_by_ai("online_forms")
    apply_stated_counts(reading, [("a.pdf", [(1, "200 services")])])
    apply_stated_counts(reading, [("b.pdf", [(1, "10 services")])])
    assert next(f for f in reading.features if f.key == "online_forms").story_units == 40

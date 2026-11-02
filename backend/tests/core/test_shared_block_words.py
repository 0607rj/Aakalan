"""A block shared with every company carries no words written about one company's feature
(OPEN_QUESTIONS 202): no description, no AI `why`, an analysis citation naming only catalog
blocks; the hours, the public pages and the name used for matching stay as they were."""

from pathlib import Path

from app.services.research.library import public_sources, public_spec, read_library

LIBRARY = Path(__file__).parents[2] / "seeds" / "research" / "library.yaml"

SOURCES = [
    {"kind": "part", "block": "master_data_management", "level": "standard", "why": "ACME clinics"},
    {"url": "https://example.org/costs", "title": "Costs", "quote": "120 hours", "ok": True},
]
SPEC = {
    "key": "researched_x",
    "name": "Multi-clinic management",
    "description": "Lets ACME run its 12 clinics.",
    "base_effort_pd": {"S": "10", "M": "20", "L": "30"},
    "evidence": [
        {
            "id": "researched_x.1",
            "citation": "AI analysis 2026-10-22: master_data_management standard (ACME clinics)",
        }
    ],
}


def test_the_shared_block_keeps_hours_and_pages_but_not_the_words() -> None:
    sources = public_sources(SOURCES)
    spec = public_spec(SPEC, sources)
    assert "ACME" not in str(spec) and "ACME" not in str(sources)
    assert spec["description"] == ""
    assert spec["evidence"][0]["citation"] == (
        "AI analysis 2026-10-22: master_data_management standard"
    )
    assert spec["base_effort_pd"] == SPEC["base_effort_pd"] and spec["name"] == SPEC["name"]
    assert sources[1] == SOURCES[1]  # a public page is shown as it is


def test_the_library_in_the_repository_is_clean() -> None:
    for e in read_library(LIBRARY):
        assert e.spec.get("description") == "", e.key
        assert all("why" not in s for s in e.sources if isinstance(s, dict)), e.key

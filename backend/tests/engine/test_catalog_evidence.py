"""Catalog v6: effort provenance for every component, eras that follow from the evidence, the
same effort numbers as v5, and catalogs v1-v5 loading unchanged."""

from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.services.engine.reference import (
    BaselineEra,
    Catalog,
    CatalogComponent,
    EffortEvidence,
    derived_era,
)
from app.services.seeding.reference import ReferenceData

PROVISIONAL_PRE_AI = {"performance_load_testing", "documentation_manuals"}
SAME_AS_V5 = (
    "key",
    "name",
    "category",
    "bucket",
    "description",
    "task_mix",
    "base_effort_pd",
    "applicable_drivers",
    "tags",
    "licence",
    "source",
)


def test_v6_eras_follow_the_evidence(reference: ReferenceData) -> None:
    v6 = reference.catalog_version("v6")
    assert len(v6.components) == 46
    pre_ai = {c.key for c in v6.components if c.source_era is BaselineEra.PRE_AI}
    assert pre_ai == PROVISIONAL_PRE_AI
    assert not [c for c in v6.components if c.source_era is BaselineEra.AI_ASSISTED]
    rules = v6.era_rules
    assert rules is not None
    for c in v6.components:
        assert c.evidence and c.confidence and c.era_reason
        assert c.source_era is derived_era(c.evidence)
        for e in c.evidence:
            if e.era is BaselineEra.PRE_AI:  # only ever from a dated, pre-cutoff source
                assert e.era_basis == "date_heuristic"
                assert e.published is not None and e.published < rules.pre_ai_before_year
    for key in PROVISIONAL_PRE_AI:
        assert "provisional" in v6.get(key).era_reason


def test_v6_keeps_every_v5_number(reference: ReferenceData) -> None:
    v5, v6 = reference.catalog_version("v5"), reference.catalog_version("v6")
    assert [c.key for c in v5.components] == [c.key for c in v6.components]
    for old, new in zip(v5.components, v6.components, strict=True):
        for field in SAME_AS_V5:
            assert getattr(old, field) == getattr(new, field), (old.key, field)


def test_calibration_basis_documents_the_multiplier(reference: ReferenceData) -> None:
    basis = reference.catalog_version("v6").calibration_basis
    assert basis is not None and basis.parameter == "calibration.effort_multiplier"
    assert not basis.reproducible and basis.limitations
    for version in basis.parameter_sets:
        calibration = reference.parameter_set(version).calibration
        assert calibration is not None
        assert calibration.effort_multiplier == Decimal("1.4")  # unchanged by catalog v6


@pytest.mark.parametrize("version", ["v1", "v2", "v3", "v4", "v5"])
def test_older_catalogs_load_without_eras(reference: ReferenceData, version: str) -> None:
    catalog = reference.catalog_version(version)
    assert catalog.era_rules is None and catalog.calibration_basis is None
    for c in catalog.components:
        assert c.source_era is None and not c.evidence
        stored = c.model_dump(mode="json")  # a v1-v5 row stored before v6 had no era fields
        for field in ("source_era", "era_reason", "confidence", "evidence"):
            stored.pop(field)
        assert CatalogComponent.model_validate(stored) == c


def evidence(**kw: object) -> dict[str, object]:
    return {
        "id": "x.1",
        "citation": "a source",
        "source_type": "vendor_estimate",
        "published": None,
        "era": "unknown",
        "era_basis": "not_established",
        "quality": "low",
        **kw,
    }


@pytest.mark.parametrize(
    "bad",
    [
        evidence(
            era="ai_assisted", era_basis="date_heuristic", published=2024
        ),  # dates never prove AI use
        evidence(era="ai_assisted"),  # not established is unknown
        evidence(era="pre_ai", era_basis="date_heuristic"),  # a date heuristic needs a year
        evidence(era="pre_ai"),
    ],
)
def test_evidence_era_rules(bad: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        EffortEvidence.model_validate(bad)


def test_component_era_must_match_its_evidence(reference: ReferenceData) -> None:
    data = reference.catalog_version("v6").get("documentation_manuals").model_dump()
    CatalogComponent.model_validate(data)
    with pytest.raises(ValidationError, match="source_era must be pre_ai"):
        CatalogComponent.model_validate({**data, "source_era": "unknown"})
    with pytest.raises(ValidationError, match="evidence needs a source_era"):
        CatalogComponent.model_validate({**data, "source_era": None})
    with pytest.raises(ValidationError, match="at least one evidence"):
        CatalogComponent.model_validate({**data, "evidence": []})


def test_dated_evidence_must_predate_the_cutoff(reference: ReferenceData) -> None:
    v6 = reference.catalog_version("v6")
    data = v6.model_dump()
    doc = next(c for c in data["components"] if c["key"] == "documentation_manuals")
    doc["evidence"][0]["published"] = 2023
    with pytest.raises(ValidationError, match="too recent"):
        Catalog.model_validate(data)

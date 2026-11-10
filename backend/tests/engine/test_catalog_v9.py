"""Catalog v9 (OPEN_QUESTIONS 229): catalog v8 with one block renamed; every key, hour and
source the same."""

from app.services.seeding.reference import ReferenceData


def test_v9_only_renames_the_forms_block(reference: ReferenceData) -> None:
    v8, v9 = reference.catalog_version("v8"), reference.catalog_version("v9")
    assert len(v9.components) == len(v8.components)
    for old, new in zip(v8.components, v9.components, strict=True):
        if old.key == "registration_empanelment":
            assert new.name == "Online forms and applications"
            assert new.model_copy(update={"name": old.name}) == old
        else:
            assert new == old

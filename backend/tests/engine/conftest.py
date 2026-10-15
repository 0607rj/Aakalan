from collections.abc import Callable
from typing import Any

import pytest

from app.core.config import get_settings
from app.services.engine.inputs import EstimateInput
from app.services.seeding.golden import golden_input
from app.services.seeding.reference import ReferenceData, load_reference


@pytest.fixture(scope="session")
def reference() -> ReferenceData:
    return load_reference(get_settings().seeds_dir)


@pytest.fixture(scope="session")
def golden(reference: ReferenceData) -> Callable[[str], EstimateInput]:
    cache: dict[str, EstimateInput] = {}

    def get(name: str) -> EstimateInput:
        if name not in cache:
            cache[name] = golden_input(name, reference)
        return cache[name]

    return get


def tweak(inp: EstimateInput, **update: Any) -> EstimateInput:
    """Copy an input with changes, re-validated."""
    data = inp.model_dump()
    data.update(update)
    return EstimateInput.model_validate(data)


def answer(inp: EstimateInput, key: str, value: object) -> EstimateInput:
    answers = [a.model_dump() for a in inp.answers if a.key != key]
    answers.append({"key": key, "value": value, "requirement_ids": []})
    return tweak(inp, answers=answers)

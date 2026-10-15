"""Quick-estimate configuration (`seeds/quick_estimate.yaml`): plain-language features and
questions that map to catalog components and questionnaire drivers. No prices live here."""

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.config import get_settings
from app.services.engine.reference import Size


class Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class Feature(Frozen):
    key: str
    label: str
    hint: str
    components: list[str]
    sets: dict[str, Any] = {}


class Option(Frozen):
    value: str | int
    label: str
    hint: str = ""
    answers: dict[str, Any]
    extra_components: list[str] = []
    component_size: Size | None = None  # scale question only


class Question(Frozen):
    label: str
    default: str | int
    options: list[Option]

    @model_validator(mode="after")
    def _default_exists(self) -> "Question":
        if self.default not in {o.value for o in self.options}:
            raise ValueError(f"default {self.default!r} is not an option")
        return self

    def option(self, value: str | int) -> Option:
        for o in self.options:
            if o.value == value:
                return o
        raise ValueError(f"{value!r} is not a valid choice")


class QuickConfig(Frozen):
    version: str
    source: str
    requirement_clarity: int = Field(ge=1, le=5)
    base_components: list[str]
    features: list[Feature]
    questions: dict[str, Question]
    plain_drivers: dict[str, str]

    def feature(self, key: str) -> Feature:
        for f in self.features:
            if f.key == key:
                return f
        raise ValueError(f"unknown feature {key!r}")


def load_quick_config(path: Path) -> QuickConfig:
    return QuickConfig.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))


@lru_cache
def quick_config() -> QuickConfig:
    return load_quick_config(get_settings().seeds_dir / "quick_estimate.yaml")

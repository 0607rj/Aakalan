"""Load and validate the reference seed YAML (taxonomy, catalog, rate cards, parameters)."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from app.services.engine.reference import Catalog, ParameterSet, RateCard, Taxonomy


def _read(path: Path) -> Any:
    with path.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


@dataclass(frozen=True)
class ReferenceData:
    taxonomy: Taxonomy
    catalog: Catalog
    rate_cards: list[RateCard]
    parameter_sets: list[ParameterSet]

    def rate_card(self, version: str) -> RateCard:
        return next(rc for rc in self.rate_cards if rc.version == version)

    def parameter_set(self, version: str) -> ParameterSet:
        return next(ps for ps in self.parameter_sets if ps.version == version)


def load_reference(seeds_dir: Path) -> ReferenceData:
    taxonomy = Taxonomy.model_validate(_read(seeds_dir / "taxonomy.yaml"))
    catalog = Catalog.model_validate(_read(seeds_dir / "catalog.yaml"))
    for c in catalog.components:
        taxonomy.bucket(c.bucket)
    rate_cards = [
        RateCard.model_validate(_read(p)) for p in sorted((seeds_dir / "rate_cards").glob("*.yaml"))
    ]
    parameter_sets = [
        ParameterSet.model_validate(_read(p))
        for p in sorted((seeds_dir / "parameters").glob("*.yaml"))
    ]
    return ReferenceData(taxonomy, catalog, rate_cards, parameter_sets)

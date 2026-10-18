"""Load and validate the reference seed YAML (taxonomy, catalog, rate cards, parameters)."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from app.services.engine.reference import (
    Catalog,
    ParameterSet,
    RateCard,
    Taxonomy,
    version_key,
)


def _read(path: Path) -> Any:
    with path.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


@dataclass(frozen=True)
class ReferenceData:
    taxonomies: list[Taxonomy]
    catalogs: list[Catalog]
    rate_cards: list[RateCard]
    parameter_sets: list[ParameterSet]

    @property
    def taxonomy(self) -> Taxonomy:
        """The newest taxonomy version."""
        return self.taxonomies[-1]

    def taxonomy_version(self, version: str) -> Taxonomy:
        return next(t for t in self.taxonomies if t.version == version)

    @property
    def catalog(self) -> Catalog:
        """The newest catalog version."""
        return self.catalogs[-1]

    def catalog_version(self, version: str) -> Catalog:
        return next(c for c in self.catalogs if c.version == version)

    def rate_card(self, version: str) -> RateCard:
        return next(rc for rc in self.rate_cards if rc.version == version)

    def parameter_set(self, version: str) -> ParameterSet:
        return next(ps for ps in self.parameter_sets if ps.version == version)


def load_reference(seeds_dir: Path) -> ReferenceData:
    taxonomies = [
        Taxonomy.model_validate(_read(p))
        for p in sorted((seeds_dir / "taxonomy").glob("*.yaml"), key=lambda p: int(p.stem[1:]))
    ]
    catalogs = [
        Catalog.model_validate(_read(p))
        for p in sorted((seeds_dir / "catalog").glob("*.yaml"), key=lambda p: int(p.stem[1:]))
    ]
    for catalog in catalogs:
        for c in catalog.components:
            taxonomies[-1].bucket(c.bucket)
    rate_cards = [
        RateCard.model_validate(_read(p))
        for p in sorted(
            (seeds_dir / "rate_cards").glob("*.yaml"), key=lambda p: version_key(p.stem)
        )
    ]
    parameter_sets = [
        ParameterSet.model_validate(_read(p))
        for p in sorted(
            (seeds_dir / "parameters").glob("*.yaml"), key=lambda p: version_key(p.stem)
        )
    ]
    return ReferenceData(taxonomies, catalogs, rate_cards, parameter_sets)

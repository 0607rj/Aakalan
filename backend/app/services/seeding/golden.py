"""Golden estimates: fixed inputs + seed ⇒ exact expected totals (brief Section 13).

Inputs live in `tests/engine/golden/<name>.yaml` and are priced against the seed reference
data. `make golden` rewrites `<name>.expected.json`; any diff must be intentional and reviewed.
"""

import json
from pathlib import Path
from typing import Any

import yaml

from app.core.config import BACKEND_DIR, get_settings
from app.services.engine.core import calculate
from app.services.engine.inputs import EstimateInput
from app.services.engine.outputs import EstimateResult
from app.services.seeding.reference import ReferenceData, load_reference

GOLDEN_DIR = BACKEND_DIR / "tests" / "engine" / "golden"
GOLDEN_NAMES = ("small", "medium", "large")
REFERENCE_VERSION = "v1"


def golden_input(name: str, reference: ReferenceData | None = None) -> EstimateInput:
    ref = reference or load_reference(get_settings().seeds_dir)
    raw: dict[str, Any] = yaml.safe_load((GOLDEN_DIR / f"{name}.yaml").read_text(encoding="utf-8"))
    raw.update(
        taxonomy=ref.taxonomy,
        catalog=ref.catalog,
        rate_card=ref.rate_card(REFERENCE_VERSION),
        parameters=ref.parameter_set(REFERENCE_VERSION),
    )
    return EstimateInput.model_validate(raw)


def summarise(result: EstimateResult) -> dict[str, Any]:
    """The reviewable fingerprint of an estimate stored in `<name>.expected.json`."""
    data = result.model_dump(mode="json")
    return {
        "engine_version": data["engine_version"],
        "versions": data["versions"],
        "feasible": data["feasible"],
        "totals": data["totals"],
        "timeline": data["timeline"],
        "by_stage": {
            g["key"]: [g["low_paise"], g["likely_paise"], g["high_paise"]] for g in data["by_stage"]
        },
        "top_drivers": data["top_drivers_text"],
        "confidence": data["confidence"]["label"],
        "calibration": data["calibration"]["status"],
        "line_count": len(data["lines"]),
        "lines": {
            ln["line_key"]: [ln["low_paise"], ln["likely_paise"], ln["high_paise"]]
            for ln in data["lines"]
        },
    }


def expected_path(name: str) -> Path:
    return GOLDEN_DIR / f"{name}.expected.json"


def write_expectations() -> list[Path]:
    ref = load_reference(get_settings().seeds_dir)
    written = []
    for name in GOLDEN_NAMES:
        summary = summarise(calculate(golden_input(name, ref)))
        path = expected_path(name)
        path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        written.append(path)
    return written

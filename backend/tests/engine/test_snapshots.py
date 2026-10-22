"""A saved estimate's input snapshot reprices to the identical result after later engine and
catalog changes (rule 3). The fixture was frozen before catalog v6 / source eras existed."""

import hashlib
import json
from pathlib import Path

from app.services.engine.core import calculate
from app.services.engine.inputs import EstimateInput

SNAPSHOTS = Path(__file__).parent / "snapshots"


def test_pre_v6_snapshot_reprices_identically() -> None:
    inp = EstimateInput.model_validate_json(
        (SNAPSHOTS / "clinic_v5_v15.input.json").read_text(encoding="utf-8")
    )
    expected = json.loads((SNAPSHOTS / "clinic_v5_v15.expected.json").read_text(encoding="utf-8"))
    assert inp.catalog.version == "v5" and inp.parameters.version == "v15"
    assert inp.era_scenario == "estimate"  # field added after the snapshot: default
    assert all(c.source_era is None for c in inp.catalog.components)
    result = calculate(inp)
    assert result.totals is not None
    assert result.totals.p50_paise == expected["p50_paise"]
    assert result.totals.likely_paise == expected["likely_paise"]
    digest = hashlib.sha256(result.model_dump_json().encode("utf-8")).hexdigest()
    assert digest == expected["result_sha256"]

"""Rate card v6: role day rates at a vendor's loaded cost (× 1.33), not its billing price
(× 1.75, which already held the vendor's profit before the estimate's own margin)."""

from decimal import Decimal
from pathlib import Path

import yaml

from app.core.config import get_settings

CARDS = Path(get_settings().seeds_dir) / "rate_cards"


def items(version: str) -> dict[str, dict[str, object]]:
    data = yaml.safe_load((CARDS / f"{version}.yaml").read_text(encoding="utf-8"))
    return {i["key"]: i for i in data["items"]}


def test_roles_lose_the_double_counted_profit() -> None:
    v5, v6 = items("v5"), items("v6")
    roles = [k for k, i in v5.items() if i["kind"] == "role"]
    assert len(roles) == 14
    for key in roles:
        old, new = Decimal(str(v5[key]["amount"])), Decimal(str(v6[key]["amount"]))
        assert abs(new - old * Decimal("1.33") / Decimal("1.75")) <= 1, key
        assert "× 1.33 ÷ 264" in str(v6[key]["source"])


def test_everything_else_is_unchanged() -> None:
    v5, v6 = items("v5"), items("v6")
    assert v5.keys() == v6.keys()
    for key, item in v5.items():
        if item["kind"] != "role":
            assert v6[key] == item, key

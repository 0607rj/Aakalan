"""Reality checks ("does this price look real?"): explain, never change a number."""

from decimal import Decimal

from app.services.quick.config import quick_config
from app.services.quick.reality import FeatureShare, reality_check


def shares(setup: int, *features: tuple[str, int]) -> list[FeatureShare]:
    return [
        FeatureShare(label="Standard", amount_paise=setup, standard=True),
        *(FeatureShare(label=n, amount_paise=a, standard=False) for n, a in features),
    ]


def run(features: list[FeatureShare], **kw: object) -> dict[str, bool]:
    rules = quick_config().reality_check
    assert rules is not None
    args: dict[str, object] = {
        "build_paise": 1_000_000,
        "run_parts_paise": {},
        "support_years": 0,
        "team_people": Decimal("3"),
        "researched": [],
        "not_sure": 0,
        **kw,
    }
    out = reality_check(rules, features, **args)  # type: ignore[arg-type]
    checks = {c.key: c.ok for c in out.checks}
    assert out.verdict == ("realistic" if all(checks.values()) else "check")
    return checks


def test_tiny_app_is_mostly_set_up() -> None:
    assert run(shares(475_000, ("To-do list", 68_000)))["setup_share"] is False
    assert run(shares(300_000, ("Forms", 400_000), ("Payments", 300_000)))["setup_share"]


def test_one_feature_dominating() -> None:
    big = shares(100, ("A", 900), ("B", 50), ("C", 50))
    assert run(big)["feature_share"] is False
    assert "feature_share" not in run(shares(100, ("A", 900), ("B", 50)))  # too few features
    assert run(shares(100, ("A", 40), ("B", 30), ("C", 30)))["feature_share"]


def test_running_team_researched_and_not_sure() -> None:
    f = shares(100, ("A", 100))
    out = run(
        f,
        run_parts_paise={"run": 3_000_000, "ai_usage": 1_000_000},
        support_years=2,
        team_people=Decimal(20),
        researched=["A"],
        not_sure=5,
    )
    assert out == {
        "setup_share": True,
        "running": False,
        "team": False,
        "researched": False,  # half the building rests on a researched block
        "not_sure": False,
    }
    assert run(f, run_parts_paise={"run": 500_000}, support_years=1)["running"]

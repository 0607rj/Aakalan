"""Each part's range is its share of the price's range and the parts add up (OPEN_QUESTIONS 167)."""

from app.services.quick.service import _shares


def test_shares_add_up_to_the_total() -> None:
    amounts = [600, 300, 100]
    assert sum(_shares(amounts, 1000, 1234)) == 1234
    assert sum(_shares(amounts, 1000, 777)) == 777
    assert _shares(amounts, 1000, 1000) == amounts


def test_the_largest_part_takes_the_rounding() -> None:
    assert _shares([600, 300, 100], 1000, 1234) == [741, 370, 123]


def test_amounts_short_of_the_planned_cost_are_only_scaled() -> None:
    assert _shares([500], 1000, 1500) == [750]

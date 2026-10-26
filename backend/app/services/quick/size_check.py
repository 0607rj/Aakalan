"""Story-size check (OPEN_QUESTIONS 163): a third build size, from the document's user stories
with a published method, set beside our feature-by-feature hours and the independent check.

Each priced feature with user stories is sized with Simple Function Points (quick config
`size_check`, every figure with its source), at the published delivery rate:

  fp          = stories × fp_per_story + stories × data_groups_per_story × fp_per_data_group
  story hours = fp × hours_per_fp[low / likely / high]
  our hours   = the feature's building cost without AI tools ÷ all building lines' cost without
                AI tools × our build hours without AI tools (the `stages`, year 0), so project
                work (management, testing, deployment) is spread as the delivery rate includes it
  ratio       = our hours ÷ story hours (likely)

Our hours with AI tools are shown beside them for the saving, never compared (the published
rate is pre-AI).

Ours agrees when it falls between the low and high story hours. Features without stories are
listed, not sized. Code only; nothing here changes a price or the range.
"""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Literal

from pydantic import BaseModel

from app.services.quick.anchor import IndependentCheckOut
from app.services.quick.config import SizeCheck

HUNDREDTH = Decimal("0.01")

Position = Literal["below", "inside", "above"]


@dataclass(frozen=True)
class SizedFeature:
    label: str
    level: str | None
    stories: int
    our_hours: Decimal  # without AI tools, project work spread in
    our_hours_with_ai: Decimal | None = None  # the same with AI tools (None: priced without)


class FeatureSize(BaseModel):
    label: str
    level: str | None  # basic / standard / advanced as priced
    stories: int
    our_hours: int
    our_hours_with_ai: int | None = None
    story_hours: int  # likely
    ratio: Decimal  # ours ÷ story hours
    position: Position
    judged: bool  # enough stories to judge alone


class SizeCheckOut(BaseModel):
    available: bool
    reason: str | None = None
    stories: int = 0
    function_points: Decimal = Decimal(0)
    story_hours_low: int = 0
    story_hours: int = 0  # likely
    story_hours_high: int = 0
    our_hours: int = 0
    our_hours_with_ai: int | None = None  # shown for the saving; never compared
    ratio: Decimal | None = None  # ours ÷ story hours (likely)
    position: Position | None = None
    count_check_ratio: Decimal | None = None  # the independent check's priced ÷ counted
    methods_agree: bool | None = None  # every method in its band; None: not like for like
    message: str = ""
    headline: str = ""  # the one plain line on the results page (no jargon)
    features: list[FeatureSize] = []  # judged features furthest from their story size first
    unsized: list[str] = []  # priced features the document gives no user stories for
    note: str = ""


NOTE = (
    "Sized from the document's user stories with Simple Function Points at the published ISBSG "
    "delivery rate (pre-AI projects, so compared with our hours without AI tools). One story is "
    "counted as one process, and the data share is a starting value: a consistency check, not "
    "proof that either size is right."
)


def function_points(rules: SizeCheck, stories: int) -> Decimal:
    """fp = stories × fp_per_story + stories × data_groups_per_story × fp_per_data_group."""
    return stories * (rules.fp_per_story + rules.data_groups_per_story * rules.fp_per_data_group)


def _hours(fp: Decimal, rate: Decimal) -> int:
    """hours = fp × hours per function point, to the hour."""
    return int((fp * rate).to_integral_value(ROUND_HALF_UP))


def _whole(hours: Decimal | None) -> int | None:
    return None if hours is None else int(hours.to_integral_value(ROUND_HALF_UP))


def _position(ours: Decimal, low: int, high: int) -> Position:
    return "below" if ours < low else "above" if ours > high else "inside"


def size_check(
    rules: SizeCheck,
    sized: list[SizedFeature],
    unsized: list[str],
    independent: IndependentCheckOut | None = None,
    reused: str | None = None,
) -> SizeCheckOut:
    """Our hours beside the story size, per feature and in total (module docstring). `reused`:
    the plain label of a build type that sets up more than it builds (no verdict then)."""
    with_stories = [f for f in sized if f.stories > 0]
    if not with_stories:
        return SizeCheckOut(
            available=False,
            reason="There are no user stories for the priced features.",
            unsized=unsized,
        )
    rate = rules.hours_per_fp
    features = []
    for f in with_stories:
        fp = function_points(rules, f.stories)
        likely = _hours(fp, rate["likely"])
        features.append(
            FeatureSize(
                label=f.label,
                level=f.level,
                stories=f.stories,
                our_hours=int(f.our_hours.to_integral_value(ROUND_HALF_UP)),
                our_hours_with_ai=_whole(f.our_hours_with_ai),
                story_hours=likely,
                ratio=(f.our_hours / likely).quantize(HUNDREDTH, ROUND_HALF_UP),
                position=_position(f.our_hours, _hours(fp, rate["low"]), _hours(fp, rate["high"])),
                judged=f.stories >= rules.min_stories,
            )
        )
    stories = sum(f.stories for f in with_stories)
    fp = function_points(rules, stories)
    low, likely, high = (_hours(fp, rate[k]) for k in ("low", "likely", "high"))
    ours = sum((f.our_hours for f in with_stories), Decimal(0))
    ai = [f.our_hours_with_ai for f in with_stories]
    ours_ai = None if None in ai else sum((h for h in ai if h is not None), Decimal(0))
    position = _position(ours, low, high)
    count_ratio = independent.ratio if independent and independent.available else None
    count_off = independent is not None and independent.available and independent.flagged
    agree = None if reused else position == "inside" and not count_off
    off = [f for f in features if f.judged and f.position != "inside"]
    off.sort(key=_distance, reverse=True)
    return SizeCheckOut(
        available=True,
        stories=stories,
        function_points=fp.quantize(HUNDREDTH, ROUND_HALF_UP),
        story_hours_low=low,
        story_hours=likely,
        story_hours_high=high,
        our_hours=int(ours.to_integral_value(ROUND_HALF_UP)),
        our_hours_with_ai=_whole(ours_ai),
        ratio=(ours / likely).quantize(HUNDREDTH, ROUND_HALF_UP),
        position=position,
        count_check_ratio=count_ratio,
        methods_agree=agree,
        message=_message(position, len(off), count_ratio is not None, agree, reused),
        headline=_headline(position, off, agree, reused),
        features=off[: rules.top_features],
        unsized=unsized,
        note=NOTE,
    )


def _distance(f: FeatureSize) -> Decimal:
    """How far a feature is from its story size, either way (ratio or its inverse)."""
    if f.ratio <= 0:
        return Decimal(10) ** 6
    return max(f.ratio, 1 / f.ratio)


NAMED = 3  # features named in the headline; the rest are counted


def _names(features: list[FeatureSize]) -> str:
    """'A, B and C' / 'A, B, C and 2 more'."""
    names = [f.label for f in features[:NAMED]]
    more = len(features) - len(names)
    if more:
        return f"{', '.join(names)} and {more} more"
    return names[0] if len(names) == 1 else f"{', '.join(names[:-1])} and {names[-1]}"


def _headline(
    position: Position, off: list[FeatureSize], agree: bool | None, reused: str | None
) -> str:
    """One plain line: whether the build size matches a standard industry method, and which
    features may be priced low or high."""
    if agree is None:
        return (
            f"Not compared with a standard industry method: built as “{reused}”, "
            "where much is set up rather than written."
        )
    if agree:
        text = "Our build size matches a standard industry method."
    else:
        side = "lower" if position == "below" else "higher"
        text = f"Our build size is {side} than a standard industry method gives."
    for side, word in (("below", "low"), ("above", "high")):
        group = [f for f in off if f.position == side]
        if group:
            n = len(group)
            text += f" {n} feature{'s' if n != 1 else ''} may be priced {word}: {_names(group)}."
    if off:
        text += " Check it." if len(off) == 1 else " Check them."
    return text


def _message(
    position: Position, off: int, counted: bool, agree: bool | None, reused: str | None
) -> str:
    methods = "three" if counted else "two"
    where = {
        "inside": "inside the size its user stories give",
        "above": "above the size its user stories give",
        "below": "below the size its user stories give",
    }[position]
    text = f"Our build hours for the features with user stories are {where}."
    if off:
        text += f" {off} feature{'s' if off != 1 else ''} to check: see the list."
    if agree is None:
        return (
            f"{reused}: much is set up rather than built, and the story size is for new code, "
            "so ours is expected to be lower. " + text
        )
    if agree:
        return f"The {methods} sizes agree. " + text
    return f"The {methods} sizes do not agree. " + text

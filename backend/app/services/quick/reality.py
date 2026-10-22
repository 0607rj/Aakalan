"""Reality checks ("does this price look real?") on a finished quick estimate. Each check
compares parts of the estimate with each other (never with market prices) and only explains;
nothing here changes a number. Thresholds come from `reality_check` in quick_estimate.yaml."""

from decimal import ROUND_HALF_UP, Decimal
from typing import Literal

from pydantic import BaseModel

from app.services.quick.config import RealityCheck

PERCENT = Decimal(100)
RUN_PARTS = ("run", "ai_usage", "services")  # paid every year after launch


class Check(BaseModel):
    key: str
    ok: bool
    title: str  # plain words, one line
    detail: str  # why, and what to look at


class RealityOut(BaseModel):
    verdict: Literal["realistic", "check"]
    checks: list[Check]


class SupportRule(BaseModel):
    """The engine's check of year-1 support against the share-of-build rule of thumb."""

    ok: bool
    message: str
    below: bool  # support is under the rule of thumb (else above it)


class FeatureShare(BaseModel):
    label: str
    amount_paise: int
    standard: bool  # the standard building blocks every project gets


def _pct(part: int, whole: int) -> int:
    return int((Decimal(part) * PERCENT / Decimal(whole)).quantize(0, rounding=ROUND_HALF_UP))


def reality_check(
    rules: RealityCheck,
    features: list[FeatureShare],
    build_paise: int,
    run_parts_paise: dict[str, int],
    support_years: int,
    team_people: Decimal | None,
    researched: list[str],
    not_sure: int,
    price_paise: int | None = None,
    emd_paise: int | None = None,
    support_rule: SupportRule | None = None,
    build_looks: Literal["high", "low"] | None = None,
) -> RealityOut:
    """Each check: ok, or a plain reason to look again. Verdict "check" if any is not ok.
    `build_looks`: what the independent check says of the build, so a support share outside
    the rule of thumb points at the side that is probably wrong."""
    checks: list[Check] = []
    work = sum(f.amount_paise for f in features)
    setup = sum(f.amount_paise for f in features if f.standard)
    own = [f for f in features if not f.standard]
    own_work = work - setup

    if work > 0:
        share = Decimal(setup) / Decimal(work)
        checks.append(
            Check(
                key="setup_share",
                ok=share <= rules.setup_share_max,
                title=f"Set-up work is {_pct(setup, work)}% of the building",
                detail="Screens design, login, testing and deployment every project needs. "
                + (
                    "That is a normal share."
                    if share <= rules.setup_share_max
                    else "Your features are a small part of this price, so it is mostly a "
                    "professional team's fixed set-up. For a very simple app, a smaller team "
                    "without formal testing, design and documents can cost much less."
                ),
            )
        )
    if len(own) >= rules.feature_share_min_features and own_work > 0:
        top = max(own, key=lambda f: f.amount_paise)
        share = Decimal(top.amount_paise) / Decimal(own_work)
        checks.append(
            Check(
                key="feature_share",
                ok=share <= rules.feature_share_max,
                title=f"Largest feature: {top.label}, {_pct(top.amount_paise, own_work)}% of "
                "the feature work",
                detail="No single feature dominates."
                if share <= rules.feature_share_max
                else "One feature costs more than all the others together. Check that its "
                "level (Basic / Standard / Advanced) is what is needed.",
            )
        )
    run_total = sum(run_parts_paise.get(k, 0) for k in RUN_PARTS)
    if support_years > 0 and build_paise > 0 and run_total > 0:
        per_year = Decimal(run_total) / Decimal(support_years)
        limit = Decimal(build_paise) * rules.run_per_year_max_of_build
        checks.append(
            Check(
                key="running",
                ok=per_year <= limit,
                title=f"A year of running costs {_pct(int(per_year), build_paise)}% of building it",
                detail="Support, hosting and usage bills are in proportion to the build."
                if per_year <= limit
                else "Running it each year costs more than building it. Check the number of "
                "users, AI use and the support level.",
            )
        )
    if team_people is not None:
        checks.append(
            Check(
                key="team",
                ok=team_people <= rules.max_average_team,
                title=f"About {team_people} people on average during the build",
                detail="A team size that fits the work."
                if team_people <= rules.max_average_team
                else "This is a large programme. Check whether the scope should be split into "
                "phases.",
            )
        )
    research_work = sum(f.amount_paise for f in own if f.label in set(researched))
    if research_work > 0 and work > 0:
        share = Decimal(research_work) / Decimal(work)
        checks.append(
            Check(
                key="researched",
                ok=share <= rules.researched_share_max,
                title=f"Features priced by research: {_pct(research_work, work)}% of the building",
                detail="Their hours are low confidence; the rest comes from the catalog."
                if share <= rules.researched_share_max
                else "A large part of the price rests on low-confidence researched blocks. "
                "Confirm their scope before quoting.",
            )
        )
    if not_sure > 0:
        checks.append(
            Check(
                key="not_sure",
                ok=not_sure <= rules.not_sure_max,
                title=f'{not_sure} answer{"s" if not_sure != 1 else ""} "Not sure"',
                detail="Each one widens the range a little."
                if not_sure <= rules.not_sure_max
                else "Many open answers make the range wide. Answering them narrows it.",
            )
        )
    if support_rule is not None and not support_rule.ok:
        checks.append(_support_share(support_rule, build_looks))
    emd_check = _emd_check(rules, price_paise, emd_paise)
    if emd_check is not None:
        checks.append(emd_check)
    verdict: Literal["realistic", "check"] = "realistic" if all(c.ok for c in checks) else "check"
    return RealityOut(verdict=verdict, checks=checks)


def _support_share(rule: SupportRule, build_looks: Literal["high", "low"] | None) -> Check:
    """Support outside its usual share of the build: a share is only as right as the build it
    is a share of, so the independent check's view of the build decides what to look at."""
    first = rule.message.split(";", 1)[0].rstrip(".") + "."
    usual = rule.message.split(";", 1)[-1].split(".", 1)[0].strip()
    if rule.below and build_looks == "high":
        detail = (
            f"{usual.capitalize()}. The independent check finds the build priced high, so "
            "support only looks small next to it: check the build first."
        )
    elif not rule.below and build_looks == "low":
        detail = (
            f"{usual.capitalize()}. The independent check finds the build priced low, so "
            "support only looks large next to it: check the build first."
        )
    else:
        detail = f"{usual.capitalize()}. Check the support hours, users and support level."
    return Check(key="support_share", ok=False, title=first, detail=detail)


PAISE_PER_CRORE = 10**9
PAISE_PER_LAKH = 10**7


def _inr(paise: Decimal) -> str:
    if paise >= PAISE_PER_CRORE:
        return f"₹{(paise / PAISE_PER_CRORE).quantize(Decimal('0.01'), ROUND_HALF_UP)} cr"
    return f"₹{(paise / PAISE_PER_LAKH).quantize(Decimal('0.1'), ROUND_HALF_UP)} lakh"


def _emd_check(rules: RealityCheck, price_paise: int | None, emd_paise: int | None) -> Check | None:
    """The tender's own EMD implies its estimated value: value = EMD ÷ share, share in
    [emd_share_min, emd_share_max]. The price (without GST: estimated values are quoted without
    it) is flagged when it is more than emd_band_factor below the lowest or above the highest
    implied value (factor 1: anywhere outside the range)."""
    if (
        not price_paise
        or not emd_paise
        or rules.emd_share_min is None
        or rules.emd_share_max is None
        or rules.emd_band_factor is None
    ):
        return None
    emd, price = Decimal(emd_paise), Decimal(price_paise)
    low, high = emd / rules.emd_share_max, emd / rules.emd_share_min
    factor = rules.emd_band_factor
    ok = low / factor <= price <= high * factor
    above = price > high * factor
    times = (price / high if above else low / price).quantize(Decimal("0.1"), ROUND_HALF_UP)
    return Check(
        key="emd_band",
        ok=ok,
        title=f"The EMD of {_inr(emd)} suggests a project value of about "
        f"{_inr(low)} to {_inr(high)}",
        detail="The price without GST fits the size the buyer expects."
        if ok
        else f"The price without GST ({_inr(price)}) is {times}x "
        + ("the top of that range. " if above else "below the bottom of that range. ")
        + (
            "Check for features counted twice, stock tender text priced as work, staff priced "
            "for too long, or work the buyer expects a ready-made product to cover."
            if above
            else "Check whether scope is missing."
        ),
    )

"""Independent check (OPEN_QUESTIONS 140): a second build estimate from what the finished system
must contain, compared with the priced build effort before the price is shared.

The bottom-up price follows the feature list, and a long tender lists more than a short brief
for the same system. This check counts what must exist instead (records, roles, screens,
selected integrations, hard problems), read from the document itself by
services/extraction/inventory.py, and sums them with the figures in quick config
`independent_check` (placeholder priors with a source). Code only; nothing here changes a
price. When the two disagree beyond the ratio band, or the price is far outside the EMD range,
a person must confirm before the estimate is exported. So must they when a document read by
the AI could not be counted (the counting call failed, or the document named too little):
the check is then missing, not passed (OPEN_QUESTIONS 186).

  anchor_pd = (entities × pd_per_entity + Σ screens × screen_weight × pd_per_screen
               + roles × pd_per_role + selected integrations × pd_per_integration
               + hard problems × pd_per_hard_problem + tenancy_pd[tenancy]) × wrapper
              × quality × ai_fit × clarity
  ratio     = priced build effort (person-days) ÷ anchor_pd
"""

from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Literal

from pydantic import BaseModel

from app.services.extraction.tender import FoundInventory
from app.services.quick.config import IndependentCheck, RealityCheck
from app.services.quick.reality import _inr

ONE = Decimal(1)
TENTH = Decimal("0.1")


class CountLine(BaseModel):
    key: str
    label: str
    count: Decimal  # screens weighted (a list, view and edit set counts 1.5)
    pd_each: Decimal
    person_days: Decimal
    items: list[str]  # what was counted, as named in the document


class Factor(BaseModel):
    label: str
    value: Decimal


class CheckLine(BaseModel):
    label: str
    amount_paise: int


class Band(BaseModel):
    system_class: str  # plain label
    size: str  # small / medium / large
    low_months: Decimal
    high_months: Decimal
    position: Literal["below", "inside", "above"]  # where the priced build sits


class IndependentCheckOut(BaseModel):
    available: bool
    reason: str | None = None  # why there is no check (e.g. no document)
    counts: list[CountLine] = []
    hard_problems: list[str] = []
    integrations_not_selected: list[str] = []  # provider not chosen: priced as an option later
    factors: list[Factor] = []
    anchor_months: Decimal | None = None  # person-months
    priced_months: Decimal | None = None
    ratio: Decimal | None = None  # priced ÷ anchor
    band: Band | None = None
    flagged: bool = False
    direction: Literal["high", "low"] | None = None
    message: str = ""
    top_lines: list[CheckLine] = []  # the largest build lines, where to look first
    emd_flagged: bool = False
    emd_message: str | None = None
    needs_confirmation: bool = False
    confirmed_at: datetime | None = None
    note: str = ""  # the figures are uncalibrated priors


NOTE = (
    "A rough second opinion from counting what the system must contain. Its figures are "
    "starting values from an outside review, not measured yet."
)


def anchor_pd(
    rules: IndependentCheck, inv: FoundInventory
) -> tuple[Decimal, list[CountLine], list[Factor]]:
    """anchor_pd and how it was made (see the module docstring)."""
    selected = [i for i in inv.integrations if i.provider_selected]
    screens = sum((rules.screen_weight.get(s.kind, ONE) for s in inv.screens), Decimal(0))
    counts = [
        CountLine(
            key="entities",
            label="Kinds of records",
            count=Decimal(len(inv.entities)),
            pd_each=rules.pd_per_entity,
            person_days=len(inv.entities) * rules.pd_per_entity,
            items=[i.name for i in inv.entities],
        ),
        CountLine(
            key="screens",
            label="Screens",
            count=screens,
            pd_each=rules.pd_per_screen,
            person_days=screens * rules.pd_per_screen,
            items=[s.name for s in inv.screens],
        ),
        CountLine(
            key="roles",
            label="User roles",
            count=Decimal(len(inv.roles)),
            pd_each=rules.pd_per_role,
            person_days=len(inv.roles) * rules.pd_per_role,
            items=[r.name for r in inv.roles],
        ),
        CountLine(
            key="integrations",
            label="Connections to named systems",
            count=Decimal(len(selected)),
            pd_each=rules.pd_per_integration,
            person_days=len(selected) * rules.pd_per_integration,
            items=[i.name for i in selected],
        ),
        CountLine(
            key="hard_problems",
            label="Hard problems",
            count=Decimal(len(inv.hard_problems)),
            pd_each=rules.pd_per_hard_problem,
            person_days=len(inv.hard_problems) * rules.pd_per_hard_problem,
            items=[rules.hard_problems.get(h.problem, h.name) for h in inv.hard_problems],
        ),
    ]
    tenancy = rules.tenancy_pd.get(inv.tenancy, Decimal(0))
    if tenancy:
        counts.append(
            CountLine(
                key="tenancy",
                label="Several organisations or regions kept apart",
                count=ONE,
                pd_each=tenancy,
                person_days=tenancy,
                items=[inv.tenancy.replace("_", " ")],
            )
        )
    engineering = sum((c.person_days for c in counts), Decimal(0))
    factors = [Factor(label="Testing, documents and deployment", value=rules.wrapper)]
    for label, table, key in (
        ("Quality demands", rules.quality, inv.quality),
        ("Fit for AI-assisted work", rules.ai_fit, inv.ai_fit),
        ("How clear the document is", rules.clarity, inv.clarity),
    ):
        if key in table:
            factors.append(Factor(label=f"{label}: {key.replace('_', ' ')}", value=table[key]))
    total = engineering
    for f in factors:
        total *= f.value
    return total, counts, factors


def _months(pd: Decimal, pd_per_month: Decimal) -> Decimal:
    return (pd / pd_per_month).quantize(TENTH, ROUND_HALF_UP)


def independent_check(
    rules: IndependentCheck,
    inv: FoundInventory | None,
    *,
    priced_pd: Decimal,
    pd_per_month: Decimal,
    project_size: str | None,
    top_lines: list[CheckLine],
    price_without_tax_paise: int | None,
    emd_paise: int | None,
    emd_rules: RealityCheck | None,
    confirmed_at: datetime | None,
    ai_read: bool = False,
) -> IndependentCheckOut:
    emd_message = _emd_block(rules, emd_rules, price_without_tax_paise, emd_paise)

    def missing(reason: str, counts: list[CountLine]) -> IndependentCheckOut:
        """No check: on a document the AI read, export waits for a person (as on a gap)."""
        if ai_read:
            reason += " Look at the price yourself before it is shared."
        return IndependentCheckOut(
            available=False,
            reason=reason,
            counts=counts,
            emd_flagged=emd_message is not None,
            emd_message=emd_message,
            needs_confirmation=ai_read or emd_message is not None,
            confirmed_at=confirmed_at,
            note=NOTE,
        )

    if inv is None:
        return missing(
            "The check could not be made: counting what the system contains failed for this "
            "document."
            if ai_read
            else "Made only for an uploaded document read by the AI.",
            [],
        )
    pd, counts, factors = anchor_pd(rules, inv)
    if pd <= 0:
        return missing(
            "The document did not name enough of what the system contains to count.", counts
        )
    ratio = (priced_pd / pd).quantize(Decimal("0.01"), ROUND_HALF_UP)
    priced_months = _months(priced_pd, pd_per_month)
    anchor_months = _months(pd, pd_per_month)
    direction: Literal["high", "low"] | None = None
    if ratio > rules.ratio_high:
        direction = "high"
    elif ratio < rules.ratio_low:
        direction = "low"
    band = _band(rules, inv.system_class, project_size, priced_months)
    if direction is None:
        message = (
            f"The priced build ({priced_months} person-months) is close to the count-based "
            f"estimate ({anchor_months} person-months)."
        )
    else:
        message = (
            f"The priced build ({priced_months} person-months) is {ratio}x the count-based "
            f"estimate ({anchor_months} person-months). "
            + (
                "Check the largest lines below for work counted twice, stock tender text "
                "priced as work, or levels set higher than the document asks."
                if direction == "high"
                else "Check whether features or screens the document names are missing."
            )
        )
    flagged = direction is not None
    return IndependentCheckOut(
        available=True,
        counts=counts,
        hard_problems=[rules.hard_problems.get(h.problem, h.name) for h in inv.hard_problems],
        integrations_not_selected=[i.name for i in inv.integrations if not i.provider_selected],
        factors=factors,
        anchor_months=anchor_months,
        priced_months=priced_months,
        ratio=ratio,
        band=band,
        flagged=flagged,
        direction=direction,
        message=message,
        top_lines=top_lines,
        emd_flagged=emd_message is not None,
        emd_message=emd_message,
        needs_confirmation=flagged or emd_message is not None,
        confirmed_at=confirmed_at,
        note=NOTE,
    )


def _band(
    rules: IndependentCheck, system_class: str, project_size: str | None, priced_months: Decimal
) -> Band | None:
    """The person-month band for this kind and size of system, and where the price sits."""
    tiers = rules.bands.get(system_class)
    size = rules.size_tier.get(project_size or "")
    if tiers is None or size is None:
        return None
    low, high = tiers[size]
    position: Literal["below", "inside", "above"] = (
        "below" if priced_months < low else "above" if priced_months > high else "inside"
    )
    return Band(
        system_class=rules.system_classes[system_class],
        size=size,
        low_months=low,
        high_months=high,
        position=position,
    )


def _emd_block(
    rules: IndependentCheck,
    emd_rules: RealityCheck | None,
    price_paise: int | None,
    emd_paise: int | None,
) -> str | None:
    """A price (without GST) more than emd_block_factor outside the value the EMD implies
    (EMD ÷ [emd_share_max, emd_share_min]) needs confirming; None when within or unknown."""
    if (
        not price_paise
        or not emd_paise
        or emd_rules is None
        or emd_rules.emd_share_min is None
        or emd_rules.emd_share_max is None
    ):
        return None
    emd, price = Decimal(emd_paise), Decimal(price_paise)
    low, high = emd / emd_rules.emd_share_max, emd / emd_rules.emd_share_min
    factor = rules.emd_block_factor
    if low / factor <= price <= high * factor:
        return None
    above = price > high
    times = (price / high if above else low / price).quantize(TENTH, ROUND_HALF_UP)
    return (
        f"The price without GST ({_inr(price)}) is {times}x "
        + ("above" if above else "below")
        + f" the {_inr(low)} to {_inr(high)} the tender's EMD suggests."
    )

"""What the review form fills in from a document's reading (the upload's "Check what we found"
screens): the starting state of every screen, and the request the form sends when the user
accepts everything it found (OPEN_QUESTIONS 161).

One function for the form (GET /documents/{id}/form) and the production-path back-test, so the
back-test prices a tender the way the app does: reading, review form, engine. The form still
works out the request itself while the user edits; untouched, it sends `ReviewPrefill.request`
(tests/core/test_prefill.py checks this against the form on the saved readings)."""

import math
from typing import Any, Literal

from pydantic import BaseModel

from app.services.engine.inputs import PaymentMilestone
from app.services.engine.reference import Size
from app.services.extraction.tender import TenderExtraction, UnclearPoint, VerifiedEvidence
from app.services.quick.config import LevelKey, Question, QuickConfig
from app.services.quick.service import CustomFeature, QuickRequest, StaffItem

Choice = str | int
HOSTING = "hosting"
INDIA = "india"
MAX_NAME = 300  # QuickRequest.name
MAX_FEATURE_NAME = 200  # CustomFeature.name
PAISE_PER_RUPEE = 100
PERCENT = 100
PERCENT_DECIMALS = 4  # the form shows a percentage to 4 decimals


class Fact(BaseModel):
    """A number the document may state, on the form's facts screen. Values are in API units
    (amounts in paise, percentages as 0-1); the limits are what the form accepts as typed
    (rupees, 0-100 for a percentage)."""

    key: str
    label: str
    hint: str = ""  # a short example under the label
    unit: Literal["count", "rupees", "percent"]
    min: int
    max: int | None = None
    integer: bool
    needs_feature: str | None = None  # shown only when this feature is ticked
    only_if_found: bool = False  # shown only when the document states it
    india_term: bool = False  # Indian bid terms: elsewhere only when the document states them
    topic: str  # the part of the form it is shown in (quick config `topics`)
    # read from the document and used (e.g. the EMD for the price check), never shown on the form
    hidden: bool = False


# fmt: off
FACTS: tuple[Fact, ...] = (
    Fact(key="users_total", label="Registered users", unit="count", min=0, integer=True, topic="users"),  # noqa: E501
    Fact(key="peak_concurrent_users", label="Users online at the same time", unit="count", min=0, integer=True, topic="users"),  # noqa: E501
    Fact(key="om_years", label="Years of support after launch", unit="count", min=0, max=10, integer=True, topic="support"),  # noqa: E501
    Fact(key="deadline_months", label="Deadline (months)", unit="count", min=1, max=60, integer=True, topic="contract"),  # noqa: E501
    Fact(key="languages", label="Languages the system must work in", hint="English and Hindi = 2", unit="count", min=1, max=30, integer=True, topic="users"),  # noqa: E501
    Fact(key="chatbot_queries_per_day", label="Chatbot questions per day", unit="count", min=0, integer=True, needs_feature="ai_chatbot", topic="users"),  # noqa: E501
    Fact(key="documents_per_month", label="Documents uploaded per month", unit="count", min=0, integer=True, only_if_found=True, topic="users"),  # noqa: E501
    Fact(key="onsite_staff", label="Staff at your office during support", unit="count", min=0, max=50, integer=True, only_if_found=True, topic="support"),  # noqa: E501
    Fact(key="support_staff", label="Dedicated support staff (offsite)", unit="count", min=0, max=50, integer=True, only_if_found=True, topic="support"),  # noqa: E501
    Fact(key="onsite_days", label="Days they are needed in all (empty = every support year)", unit="count", min=1, max=2000, integer=True, only_if_found=True, topic="support"),  # noqa: E501
    Fact(key="emd_paise", label="EMD amount", unit="rupees", min=0, integer=False, india_term=True, topic="contract", hidden=True),  # noqa: E501
    Fact(key="pbg_percent", label="Performance guarantee (%)", unit="percent", min=0, max=100, integer=False, india_term=True, topic="contract"),  # noqa: E501
)
# fmt: on


class FactValue(Fact):
    value: int | float | None  # the document's number (API units); None = not stated


class FoundStaff(StaffItem):
    """A staff line as priced from the document, with how and where it says so."""

    why: str  # how it was priced, in plain words
    evidence: list[VerifiedEvidence]


# The answers that move a tender's price most (OPEN_QUESTIONS 162), on the form's first review
# screen: the staff list, then form questions. A reading's pre-bid queries name the answer they
# affect (UnclearPoint.answer); staff queries belong to the staff list.
KeyAnswerKey = Literal["staff", "support_hours", "support_years", "build_type", "chatbot_task"]
STAFF: Literal["staff"] = "staff"
OM_YEARS = "om_years"
CHATBOT_FEATURE = "ai_chatbot"
KEY_QUESTIONS: tuple[KeyAnswerKey, ...] = (
    "support_hours",
    "support_years",
    "build_type",
    "chatbot_task",
)
QUERY_ANSWER: dict[str, KeyAnswerKey] = {
    "onsite_staff": STAFF,
    "support_staff": STAFF,
    "support_hours": "support_hours",
    "support_years": "support_years",
    "build_type": "build_type",
    "chatbot_level": "chatbot_task",
}


class KeyAnswer(BaseModel):
    """One of the answers that move the price most, with the clause that gives it and the
    pre-bid queries about it. The form orders them by `impact_paise` (GET /documents/{id}/form)."""

    key: KeyAnswerKey
    label: str
    value: str  # the answer as priced, in plain words
    stated: bool  # the document gives it (else the usual answer)
    evidence: list[VerifiedEvidence]
    queries: list[UnclearPoint]
    # how far the other answers move the most likely price (None: not worked out)
    impact_paise: int | None = None


class ReviewPrefill(BaseModel):
    """The review form's starting state, and what it sends when everything is accepted."""

    country: str
    name: str
    features: list[str]  # ticked (a mobile app, other software, old data: through `choices`)
    choices: dict[str, Choice]
    answered: list[str]  # answers the document gives (the rest print as assumed)
    levels: dict[str, LevelKey]  # each found feature's level from its user stories
    facts: list[FactValue]
    custom_features: list[CustomFeature]  # found in the document (`found_index`), included
    scope: list[str]  # what the document asks for (explicit), ticked
    payment_schedule: list[PaymentMilestone] | None  # the document's payment terms
    # staff during support priced from the document's staff lines (None: the reading has none,
    # so the onsite_staff / support_staff facts are used)
    staff: list[FoundStaff] | None = None
    key_answers: list[KeyAnswer] = []
    request: QuickRequest


def form_country(cfg: QuickConfig, country: str) -> str:
    """The country the form is for: the one asked, else the first switched on."""
    enabled = [k for k, c in cfg.countries.items() if c.enabled]
    return country if country in enabled else enabled[0]


def form_questions(cfg: QuickConfig, country: str) -> dict[str, Question]:
    """The questions the form shows (not the company's own settings), hosting limited to the
    options available in `country` (its default the first available when the usual one is
    not)."""
    allowed = cfg.countries[form_country(cfg, country)].hosting_options
    out: dict[str, Question] = {}
    for key, q in cfg.questions.items():
        if q.group == "hidden":
            continue
        if any(o.retired for o in q.options):
            q = q.model_copy(update={"options": [o for o in q.options if not o.retired]})
        if key == HOSTING:
            shown = [o for o in q.options if o.answers.get("hosting_provider") in allowed]
            default = q.default if q.default in [o.value for o in shown] else shown[0].value
            q = q.model_copy(update={"options": shown, "default": default})
        out[key] = q
    return out


def default_for(q: Question, choices: dict[str, Choice]) -> Choice:
    """A question's default given the other answers (`default_by`)."""
    for other, by_value in q.default_by.items():
        value = by_value.get(str(choices.get(other)))
        if value is not None:
            return value
    return q.default


def initial_choices(questions: dict[str, Question], given: dict[str, Choice]) -> dict[str, Choice]:
    """The given answers, then defaults that follow them; must-choose questions stay open."""
    asked = {k: q for k, q in questions.items() if not q.must_choose or k in given}
    base = {k: given.get(k, q.default) for k, q in asked.items()}
    for k, q in asked.items():
        if k not in given:
            base[k] = default_for(q, base)
    return base


def preset_from_features(questions: dict[str, Question], keys: set[str]) -> dict[str, Choice]:
    """Answers implied by found features asked as questions (a mobile app found -> "website
    and a mobile app"): each question's first plain option that adds one of them."""
    out: dict[str, Choice] = {}
    for k, q in questions.items():
        match = next((o for o in q.options if not o.unsure and set(o.add_features) & keys), None)
        if match is not None:
            out[k] = match.value
    return out


def all_features(
    questions: dict[str, Question], ticked: list[str], choices: dict[str, Choice]
) -> list[str]:
    """Ticked features plus those the chosen answers add, in that order."""
    added: list[str] = []
    for k, q in questions.items():
        value = choices.get(k, q.default)
        option = next((o for o in q.options if o.value == value), None)
        added += list(option.add_features) if option else []
    return list(dict.fromkeys([*ticked, *added]))


def answers_from_numbers(
    questions: dict[str, Question], numbers: dict[str, int | float]
) -> dict[str, Choice]:
    """A stated number answers its question: e.g. 50,000 registered users pick the smallest
    scale option whose max_users covers them (an option with no limit covers everything)."""
    out: dict[str, Choice] = {}
    for k, q in questions.items():
        n = numbers.get(q.answered_by_number) if q.answered_by_number else None
        if n is None:
            continue
        fits = sorted(
            (o for o in q.options if not o.unsure and (o.max_users is None or o.max_users >= n)),
            key=lambda o: math.inf if o.max_users is None else o.max_users,
        )
        if fits:
            out[k] = fits[0].value
    return out


def _number(value: Any) -> float | None:
    """The document's value as a number, as the form reads it (None: not a number)."""
    if isinstance(value, bool) or value is None:
        return None
    try:
        n = float(value)
    except (TypeError, ValueError):
        return None
    return n if math.isfinite(n) else None


def _js_round(x: float) -> int:
    """Math.round: halves round up."""
    return math.floor(x + 0.5)


def _as_typed(fact: Fact, value: Any) -> float | None:
    """The number the form shows for a document value (rupees; 0-100 for a percentage)."""
    n = _number(value)
    if n is None:
        return None
    if fact.unit == "rupees":
        return n / PAISE_PER_RUPEE
    if fact.unit == "percent":
        return round(n * PERCENT, PERCENT_DECIMALS)
    return n


def _valid(fact: Fact, typed: float) -> bool:
    """The form accepts it: a whole number where one is needed, within the limits."""
    if fact.integer and not typed.is_integer():
        return False
    return typed >= fact.min and (fact.max is None or typed <= fact.max)


def _to_api(fact: Fact, typed: float) -> int | float:
    if fact.unit == "rupees":
        return _js_round(typed * PAISE_PER_RUPEE)
    if fact.unit == "percent":
        return typed / PERCENT
    return int(typed) if typed.is_integer() else typed


def _size(value: str) -> Size:
    """S or L as found, anything else medium."""
    return Size(value) if value in ("S", "L") else Size("M")


def _found_choice(found: Any) -> Choice | None:
    value = getattr(found, "value", None)
    return value if isinstance(value, str | int) and not isinstance(value, bool) else None


def review_prefill(cfg: QuickConfig, extraction: TenderExtraction, country: str) -> ReviewPrefill:
    """The review form for a document's reading: features it asks for ticked (those mentioned
    only in passing in a long document are not), its answers and numbers filled in, the rest
    at the usual answer, each feature at the level its user stories give, its other features
    and explicit scope items included, its payment terms used."""
    country = form_country(cfg, country)
    questions = form_questions(cfg, country)
    found_features = {f.key: f for f in extraction.features}
    suggested = [
        f for f in cfg.features if f.key in found_features and found_features[f.key].suggested
    ]
    features = [f.key for f in suggested if not f.hidden]
    found = {k: v for k in questions if (v := _found_choice(extraction.choices.get(k))) is not None}
    preset = preset_from_features(questions, {f.key for f in suggested if f.hidden})
    choices = initial_choices(questions, {**preset, **found})
    answered = list(dict.fromkeys([*found, *preset]))
    everything = all_features(questions, features, choices)

    facts = [
        FactValue(**fact.model_dump(), value=_api_value(fact, extraction.numbers.get(fact.key)))
        for fact in FACTS
    ]
    overrides: dict[str, int | float] = {}
    for fact in facts:
        stated = fact.key in extraction.numbers
        shown = (
            (fact.needs_feature is None or fact.needs_feature in features)
            and (not fact.only_if_found or stated)
            and (not fact.india_term or country == INDIA or stated)
        )
        typed = _as_typed(fact, fact.value)
        if shown and typed is not None and _valid(fact, typed):
            overrides[fact.key] = _to_api(fact, typed)
    by_number = answers_from_numbers(questions, overrides)

    levels: dict[str, LevelKey] = {
        f.key: f.story_level for f in extraction.features if f.story_level
    }
    leveled = {f.key for f in cfg.features if f.levels}
    custom = [
        CustomFeature(
            name=o.name.strip()[:MAX_FEATURE_NAME],
            category=o.category,
            size=_size(o.size),
            found_index=i,
            units=o.units,
        )
        for i, o in enumerate(extraction.other_features)
        if o.name.strip()
    ]
    scope = [s.key for s in extraction.scope if s.status == "explicit"]
    applicable = {
        i.key for g in cfg.scope if g.feature is None or g.feature in everything for i in g.items
    }
    terms = extraction.payment_terms
    schedule = (
        [
            PaymentMilestone(
                at_build_fraction=p.at_build_fraction,
                offset_months=p.offset_months,
                percent=p.percent,
            )
            for p in terms.payments
        ]
        if terms
        else None
    )
    staff = (
        [
            FoundStaff(
                kind=p.kind,
                role=p.role[:MAX_FEATURE_NAME],
                count=p.count,
                months=p.months,
                seats=p.seats,
                call_off=p.call_off,
                found_index=i,
                why=p.why,
                evidence=p.evidence,
            )
            for i, p in enumerate(extraction.staffing)
        ]
        if extraction.staffing is not None
        else None
    )
    name = extraction.project_name
    request = QuickRequest(
        mode="vendor",
        name=(name.strip() or "Estimate")[:MAX_NAME],
        country=country,
        features=features,
        feature_levels={k: v for k, v in levels.items() if k in everything and k in leveled},
        feature_units={
            f.key: f.story_units
            for f in extraction.features
            if f.story_units > 1 and f.key in everything
        },
        custom_features=custom,
        choices={**choices, **by_number},
        scope=[k for k in scope if k in applicable],
        overrides=overrides,
        not_included=[],
        answered=list(dict.fromkeys([*answered, *by_number])),
        payment_schedule=schedule,
        staff=[StaffItem(**s.model_dump(include=set(StaffItem.model_fields))) for s in staff]
        if staff is not None
        else None,
    )
    return ReviewPrefill(
        country=country,
        name=name,
        features=features,
        choices=choices,
        answered=answered,
        levels=levels,
        facts=facts,
        custom_features=custom,
        scope=scope,
        payment_schedule=schedule,
        staff=staff,
        key_answers=key_answers(cfg, extraction, questions, request, staff, everything),
        request=request,
    )


def _staff_words(staff: list[FoundStaff]) -> str:
    if not staff:
        return "No staff during support"
    parts = []
    for s in staff:
        where = "onsite" if s.kind == "onsite" else "offsite"
        count = f"{s.count.normalize():f}" + (" round-the-clock seats" if s.seats else "")
        months = f", {s.months} months" if s.months else ""
        parts.append(f"{count} {s.role} ({where}{months})")
    return "; ".join(parts)


def key_answers(
    cfg: QuickConfig,
    extraction: TenderExtraction,
    questions: dict[str, Question],
    request: QuickRequest,
    staff: list[FoundStaff] | None,
    everything: list[str],
) -> list[KeyAnswer]:
    """The staff list (when the reading has staff lines), support hours, support years, build
    type and the chatbot's level (when it has one), each with its clause and pre-bid queries,
    in this order until priced (the API orders them by impact)."""
    queries: dict[str, list[UnclearPoint]] = {}
    for u in extraction.unclear_points:
        answer = QUERY_ANSWER.get(u.answer)
        if answer is not None:
            queries.setdefault(answer, []).append(u)
    out: list[KeyAnswer] = []
    if staff is not None:
        out.append(
            KeyAnswer(
                key=STAFF,
                label="Staff during support",
                value=_staff_words(staff),
                stated=bool(staff),
                evidence=[e for s in staff for e in s.evidence[:1]],
                queries=queries.get(STAFF, []),
            )
        )
    for key in KEY_QUESTIONS:
        q = questions.get(key)
        if q is None or (key == "chatbot_task" and CHATBOT_FEATURE not in everything):
            continue
        found = extraction.choices.get(key)
        value = request.choices.get(key, q.default)
        label = next((o.label for o in q.options if o.value == value), str(value))
        evidence = list(found.evidence) if found is not None else []
        stated = found is not None and found.value == value
        years = extraction.numbers.get(OM_YEARS)
        if key == "support_years" and OM_YEARS in request.overrides and years is not None:
            label, evidence, stated = f"{request.overrides[OM_YEARS]} years", years.evidence, True
        out.append(
            KeyAnswer(
                key=key,
                label=q.label,
                value=label,
                stated=stated,
                evidence=evidence,
                queries=queries.get(key, []),
            )
        )
    return out


def _api_value(fact: Fact, found: Any) -> int | float | None:
    """The document's number for a fact, as stored (None when not stated or not a number)."""
    n = _number(getattr(found, "value", None))
    if n is None:
        return None
    return int(n) if n.is_integer() and fact.unit != "percent" else n

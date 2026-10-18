# ruff: noqa: E501  (regex tables read better on one line)
"""Basic tender reader — no AI, no API key. Finds features and choices by keywords from
`seeds/quick_estimate.yaml` and common tender phrasings for numbers (users, O&M years,
deadline, languages, EMD, PBG, onsite staff) and things it does not price (penalties, warranty,
payment terms...). It produces the same `ExtractionOutput` as the AI reader, and
every finding quotes the exact sentence it matched, so the same citation check applies.
It is deliberately conservative: it misses unusual wording rather than guessing.
"""

import re
from collections.abc import Iterator

from app.services.documents.parsing import ParsedDocument
from app.services.extraction.tender import (
    ChoiceFinding,
    Evidence,
    ExtractionOutput,
    FeatureFinding,
    NotPricedFinding,
    NumberFinding,
    UnclearFinding,
)
from app.services.quick.config import QuickConfig

MAX_EVIDENCE = 2
MAX_UNCLEAR = 12  # keep the pre-bid list readable
MAX_QUOTE_CHARS = 300
CLAUSE = re.compile(r"(?m)^\s*(\d{1,2}(?:\.\d{1,3}){1,4})\b")
SENTENCE_END = re.compile(r"(?<=[.;:!?])\s+|\n")
# Unit words, not tunable parameters.
SCALE_WORDS = {"lakh": 100_000, "lakhs": 100_000, "lac": 100_000, "lacs": 100_000,
               "crore": 10_000_000, "crores": 10_000_000, "million": 1_000_000}  # fmt: skip
NUMBER_WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
                "eight": 8, "nine": 9, "ten": 10, "twelve": 12}  # fmt: skip
DAYS_PER_MONTH = 30
WEEKS_PER_MONTH = 4
NUM = r"(\d[\d,]*(?:\.\d+)?|one|two|three|four|five|six|seven|eight|nine|ten|twelve)"
SCALE = r"\s*(lakhs?|lacs?|crores?|million)?"

NUMBER_PATTERNS: dict[str, list[re.Pattern[str]]] = {
    "om_years": [
        re.compile(NUM + r"\s*(?:\(\w+\)\s*)?years?\s+(?:of\s+)?(?:o\s*&\s*m|operations?\s+(?:and|&)\s+maintenance|amc|maintenance|post[- ]implementation support)", re.I),
        re.compile(r"(?:o\s*&\s*m|operations?\s+(?:and|&)\s+maintenance|amc)[^.\n]{0,60}?(?:period\s+of\s+|for\s+)" + NUM + r"\s*(?:\(\w+\)\s*)?years?", re.I),
    ],
    "deadline_months": [
        re.compile(r"(?:go[- ]live|implementation|completion|complete|deliver\w*)[^.\n]{0,80}?within\s+" + NUM + r"\s*(?:\(\w+\)\s*)?(months?|weeks?|days?)", re.I),
        re.compile(r"within\s+" + NUM + r"\s*(?:\(\w+\)\s*)?(months?|weeks?|days?)\s+(?:of|from)\s+(?:the\s+)?(?:date\s+of\s+)?(?:issue\s+of\s+)?(?:work\s+order|loa|loi|award|signing)", re.I),
    ],
    "peak_concurrent_users": [
        re.compile(NUM + SCALE + r"\s+(?:concurrent|simultaneous)\s+users", re.I),
        re.compile(r"(?:concurrent|simultaneous)\s+users[^.\n]{0,30}?" + NUM + SCALE, re.I),
    ],
    "users_total": [
        re.compile(NUM + SCALE + r"\s+(?:registered\s+|expected\s+|total\s+)?(?:users|citizens|vendors|applicants|beneficiaries|stakeholders)\b", re.I),
    ],
    "languages": [
        re.compile(NUM + r"\s+(?:indian\s+|regional\s+|official\s+|scheduled\s+)?languages", re.I),
    ],
    "chatbot_queries_per_day": [
        re.compile(NUM + SCALE + r"\s+(?:queries|conversations|chats|interactions)\s+(?:per|a|each)\s+day", re.I),
    ],
    "emd_rupees": [
        re.compile(r"(?:emd|earnest\s+money\s+deposit)[^.\n]{0,80}?(?:rs\.?|inr|₹)\s*" + NUM + SCALE, re.I),
    ],
    "pbg_percent": [
        re.compile(r"(?:performance\s+(?:bank\s+)?(?:guarantee|security)|pbg)[^.\n]{0,80}?(\d+(?:\.\d+)?)\s*%", re.I),
    ],
    "onsite_staff": [
        re.compile(NUM + r"\s*(?:\(\w+\)\s*)?(?:nos\.?\s+|numbers?\s+of\s+)?(?:qualified\s+)?(?:resident|onsite|on-site|on\s+site)\s+(?:support\s+)?(?:engineers?|staff|personnel|manpower|developers?|resources?)", re.I),
    ],
}  # fmt: skip


def _value(token: str, scale: str | None = None) -> float:
    word = token.lower()
    base = float(NUMBER_WORDS[word]) if word in NUMBER_WORDS else float(word.replace(",", ""))
    return base * SCALE_WORDS.get((scale or "").lower(), 1)


def _sentence(text: str, start: int, end: int) -> str:
    """The sentence (or line) containing text[start:end], verbatim, trimmed to a sane length."""
    bounds = [m.end() for m in SENTENCE_END.finditer(text, 0, start)]
    s = bounds[-1] if bounds else 0
    tail = SENTENCE_END.search(text, end)
    e = tail.start() + 1 if tail else len(text)
    quote = text[s:e].strip()
    if len(quote) > MAX_QUOTE_CHARS:  # keep a verbatim window around the match
        s = max(s, start - MAX_QUOTE_CHARS // 3)
        quote = text[s : min(e, s + MAX_QUOTE_CHARS)].strip()
    return quote


def _clause(text: str, pos: int) -> str:
    found = [m.group(1) for m in CLAUSE.finditer(text, 0, pos)]
    return found[-1] if found else ""


def _evidence(
    doc: ParsedDocument, pattern: re.Pattern[str]
) -> Iterator[tuple[Evidence, re.Match[str]]]:
    for page in doc.pages:
        for m in pattern.finditer(page.text):
            quote = _sentence(page.text, m.start(), m.end())
            yield (
                Evidence(page=page.number, clause_ref=_clause(page.text, m.start()), quote=quote),
                m,
            )


def _is_clause_number(m: re.Match[str]) -> bool:
    """A number at the start of a line is a clause number ("4.1 Vendors shall…"), not a count."""
    start = m.start(1)
    before = m.string[:start].rstrip(" \t")
    at_line_start = before == "" or before.endswith("\n")
    return at_line_start and bool(re.match(r"\d+\.\d", m.string[start:]))


def _phrase(words: list[str]) -> re.Pattern[str]:
    alternatives = "|".join(
        re.escape(w).replace(r"\ ", r"\s+") for w in sorted(words, key=len, reverse=True)
    )
    return re.compile(rf"(?<![\w.])(?:{alternatives})(?![\w])", re.I)


# A deadline found next to these words is about paperwork (bank guarantee, signing, deposits),
# not about delivering the software: "submit the PBG within 15 days of award".
NOT_DELIVERY = re.compile(
    r"\b(pbg|performance\s+(?:bank\s+)?(?:guarantee|security)|bank\s+guarantee|security\s+deposit"
    r"|emd|earnest|agreement|sign(?:ed|ing)?|submit\w*|invoice|payment|bill|claim|refund"
    r"|clarification|query|queries|representation|objection)\b",
    re.I,
)


def basic_read(cfg: QuickConfig, doc: ParsedDocument) -> ExtractionOutput:
    long_doc = len(doc.pages) >= cfg.keywords.long_document_pages
    features = []
    for key, words in cfg.keywords.features.items():
        all_hits = [ev for ev, _ in _evidence(doc, _phrase(words))]
        if all_hits:
            mentions = len({(ev.page, ev.quote) for ev in all_hits})
            # In a long document a feature named once or twice is often boilerplate
            # ("payment terms", "dashboard of bids"): offer it, but do not tick it.
            suggested = not long_doc or mentions >= cfg.keywords.min_mentions_long_document
            features.append(
                FeatureFinding(
                    key=key,
                    evidence=all_hits[:MAX_EVIDENCE],
                    mentions=mentions,
                    suggested=suggested,
                )
            )

    numbers: list[NumberFinding] = []
    for field, patterns in NUMBER_PATTERNS.items():
        for pattern in patterns:
            match = next(
                (
                    (ev, m)
                    for ev, m in _evidence(doc, pattern)
                    if not _is_clause_number(m)
                    and not (field == "deadline_months" and NOT_DELIVERY.search(ev.quote))
                ),
                None,
            )
            if match is None:
                continue
            ev, m = match
            groups = [g for g in m.groups() if g is not None]
            value = _value(
                groups[0],
                groups[1] if len(groups) > 1 and groups[1].lower() in SCALE_WORDS else None,
            )
            unit = groups[-1].lower() if field == "deadline_months" else ""
            if unit.startswith("week"):
                value = -(-value // WEEKS_PER_MONTH)
            elif unit.startswith("day"):
                value = -(-value // DAYS_PER_MONTH)
            numbers.append(NumberFinding(field=field, value=value, evidence=[ev]))
            break

    choices = []
    for question, options in cfg.keywords.choices.items():
        for option, words in options.items():  # options are listed strongest first
            hit = next(_evidence(doc, _phrase(words)), None)
            if hit:
                choices.append(ChoiceFinding(question=question, value=option, evidence=[hit[0]]))
                break
    users = next((n for n in numbers if n.field == "users_total"), None)
    if users is not None:
        for scale_option in cfg.questions["scale"].options:
            if scale_option.max_users is None or users.value <= scale_option.max_users:
                choices.append(
                    ChoiceFinding(
                        question="scale", value=str(scale_option.value), evidence=users.evidence
                    )
                )
                break

    unclear: list[UnclearFinding] = []
    seen: set[tuple[int, str]] = set()
    for ev, m in _evidence(doc, _phrase(cfg.prebid.vague_phrases)):
        if (ev.page, ev.quote) in seen or len(unclear) >= MAX_UNCLEAR:
            continue
        seen.add((ev.page, ev.quote))
        clause = ev.clause_ref or "(unnumbered)"
        unclear.append(
            UnclearFinding(
                topic=f'Vague wording: "{m.group(0).strip()}"',
                why="The scope or quantity is not specified.",
                page=ev.page,
                clause_ref=ev.clause_ref,
                quote=ev.quote,
                prebid_query=cfg.prebid.vague_query.format(
                    clause=clause, page=ev.page, quote=ev.quote
                ),
            )
        )

    not_priced = []
    for topic, rule in cfg.not_priced_topics.items():
        hits = [ev for ev, _ in _evidence(doc, _phrase(rule.words))]
        if hits:
            not_priced.append(NotPricedFinding(topic=topic, evidence=hits[:MAX_EVIDENCE]))

    first_lines = [ln.strip() for ln in doc.pages[0].text.splitlines() if len(ln.strip()) > 10]
    return ExtractionOutput(
        project_name=first_lines[0][:150] if first_lines else "New estimate",
        summary=(
            f"Read without AI: found {len(features)} features and {len(numbers)} numbers by "
            "keyword. Please check every item and add any features that were missed."
        ),
        features=features,
        other_features=[],
        choices=choices,
        numbers=numbers,
        unclear_points=unclear,
        not_priced=not_priced,
    )

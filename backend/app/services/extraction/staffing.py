"""Staff, support hours, helpdesk and chatbot level, decided in code from the reading's staff
lines (prompt v9) and the page text (OPEN_QUESTIONS 162). The reader only finds and quotes the
statements; these rules decide what is priced, the same way for every tender:

1. A priced staff table (BoQ, commercial format) wins over narrative terms. A narrative statement
   about the same staff (`same_staff_as`) is not priced again; when it states another number or
   place, a pre-bid query quotes both.
2. Staffed round-the-clock support only for a committed team in shifts or on a roster. Round-the-
   clock wording otherwise (support, operations, uptime, availability) is on call.
3. Call-off staff (the buyer sets the headcount) are priced as written, never multiplied by
   shifts, with a pre-bid query; a call-off team "on 24x7" is on call. A committed
   round-the-clock team stated per shift is priced as seats: the engine multiplies them by the
   people per round-the-clock seat (parameters), shown in the trace as an assumption.
4. Place not stated: priced offsite (as support staff), with a pre-bid query.
5. How long comes from the staff line (months from the start of support), not the contract.
   Staff needed only for the build are part of the build's effort, not priced here.
6. An unclear quantity is priced as read, with a pre-bid query.
7. Helpdesk only when the document asks for a complaint desk, service desk or helpdesk staff.
8. The chatbot handles "complex questions" only when it must connect to the buyer's own systems.

Pricing both readings of an unclear statement (a wider range) is not done (switched off until
the back-test shows it improves coverage)."""

import re
from collections.abc import Iterable, Iterator
from decimal import Decimal
from typing import Literal

from app.models import Document
from app.services.extraction.client_provided import sentences
from app.services.extraction.tender import (
    FoundStaffLine,
    FoundValue,
    PricedStaff,
    TenderExtraction,
    UnclearPoint,
    VerifiedEvidence,
)
from app.services.quick.config import QuickConfig, Staffing, SupportTerms

ONSITE: Literal["onsite"] = "onsite"
SUPPORT: Literal["support"] = "support"
SUPPORT_HOURS, HELPDESK, CHATBOT = "support_hours", "helpdesk_scope", "chatbot_task"
CHATBOT_FEATURE = "ai_chatbot"
ALWAYS, ON_CALL, OFFICE = "always", "on_call", "office"
YES, ADVANCED = "yes", "advanced"
STAFF_NUMBERS = ("onsite_staff", "support_staff")  # replaced by the priced staff lines
FIRST_STAFF_PROMPT = 9  # extract_tender_v9 reads staff lines and the chatbot's systems
PLACES = {
    "client_site": "at the client's site",
    "vendor_site": "offsite",
    "not_stated": "place not stated",
}
MAX_MONTHS = 240


def reads_staff(extraction: TenderExtraction) -> bool:
    """The reading has staff lines and the chatbot's systems (prompt v9 or later, or entered by
    hand): only then do the staff and chatbot rules replace the older answers."""
    found = re.search(r"extract_tender_v(\d+)", extraction.prompt_version)
    return bool(extraction.staff_lines) or (
        found is not None and int(found[1]) >= FIRST_STAFF_PROMPT
    )


def _norm(text: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", text.lower()))


def _has(text: str, phrases: Iterable[str]) -> bool:
    low = text.lower()
    return any(re.search(rf"(?<!\w){re.escape(p.lower())}(?!\w)", low) for p in phrases)


def _n(value: Decimal) -> str:
    """2, 0.5: a count as written."""
    return f"{value.normalize():f}"


def _query(
    template: str, line: FoundStaffLine, answer: str, topic: str, **extra: str
) -> UnclearPoint:
    ev = line.evidence[0]
    text = template.format(
        role=line.role,
        count=_n(line.count) if line.count > 0 else "an unstated number of",
        place=PLACES[line.location],
        page=ev.page,
        note=line.note or "people, months or years",
        **extra,
    )
    return UnclearPoint(
        topic=topic,
        why=line.note or text.split(". ")[0] + ".",
        page=ev.page,
        clause_ref=ev.clause_ref,
        quote=ev.quote,
        prebid_query=text,
        answer=answer,
        document=ev.document,
    )


def _differs(narrative: FoundStaffLine, table: FoundStaffLine) -> bool:
    """A narrative statement says another number or place than the price-table row."""
    count = narrative.count > 0 and (
        narrative.count != table.count or narrative.count_basis != table.count_basis
    )
    places = {narrative.location, table.location} - {"not_stated"}
    return count or len(places) > 1


def _priced(rules: Staffing, line: FoundStaffLine, queries: list[UnclearPoint]) -> PricedStaff:
    """One staff line as priced staff, with the queries its rules raise (rules 3 to 6)."""
    kind = ONSITE if line.location == "client_site" else SUPPORT
    answer = "onsite_staff" if kind == ONSITE else "support_staff"
    count, months, seats, why = line.count, line.months, False, []
    if line.location == "not_stated":
        queries.append(
            _query(rules.queries.place_not_stated, line, answer, f"Where the {line.role} sit")
        )
        why.append("place not stated: priced offsite")
    if line.count_basis == "resource_months":
        months = min(max(round(line.count), 1), MAX_MONTHS)
        count = Decimal(1)
        why.append(f"{_n(line.count)} resource-months: priced as one person for {months} months")
    call_off = line.buyer_sets_headcount
    if call_off:
        queries.append(_query(rules.queries.call_off, line, answer, f"Number of {line.role}"))
        why.append("the buyer sets the headcount: priced as written")
    elif line.count_basis == "per_shift" and line.round_the_clock:
        seats = True
        why.append(f"{_n(count)} per shift round the clock: priced as round-the-clock seats")
    if line.quantity_unclear:
        queries.append(
            _query(rules.queries.quantity_unclear, line, answer, f"Number of {line.role}")
        )
        why.append("number unclear: priced as read")
    why.append(f"for {months} months" if months else "every support year")
    return PricedStaff(
        kind=kind,
        role=line.role,
        count=count,
        seats=seats,
        months=months,
        call_off=call_off,
        why="; ".join(why),
        evidence=list(line.evidence),
    )


def price_staff(
    rules: Staffing, lines: list[FoundStaffLine]
) -> tuple[list[PricedStaff], list[UnclearPoint]]:
    """The staff to price from the reading's staff lines (rules 1, 3 to 6), and the pre-bid
    queries they raise. The same staff stated twice in the same way is priced once."""
    table = {_norm(line.role): line for line in lines if line.in_price_table}
    # a price-table row that does not say where the staff sit takes the place its narrative
    # statement gives ("two IT Developers ... working remotely")
    for line in lines:
        row = table.get(_norm(line.same_staff_as)) if not line.in_price_table else None
        if row is not None and row.location == "not_stated" and line.location != "not_stated":
            table[_norm(row.role)] = row.model_copy(update={"location": line.location})
    lines = [table.get(_norm(x.role), x) if x.in_price_table else x for x in lines]
    queries: list[UnclearPoint] = []
    priced: list[PricedStaff] = []
    seen: set[tuple[object, ...]] = set()
    for line in lines:
        if line.phase == "build":
            continue  # people only for the build are the build's effort
        linked = (
            table.get(_norm(line.same_staff_as))
            if not line.in_price_table and line.same_staff_as
            else None
        )
        if linked is not None:  # rule 1: the price table is priced, not this statement
            if _differs(line, linked):
                ev = linked.evidence[0]
                queries.append(
                    _query(
                        rules.queries.table_conflict,
                        line,
                        "onsite_staff" if linked.location == "client_site" else "support_staff",
                        f"Number or place of {linked.role}",
                        table_role=linked.role,
                        table_count=_n(linked.count),
                        table_place=PLACES[linked.location],
                        table_page=str(ev.page),
                    )
                )
            continue
        if line.count <= 0:
            continue
        staff = _priced(rules, line, queries)
        key = (staff.kind, _norm(staff.role), staff.count, staff.months, staff.seats)
        if key not in seen:
            seen.add(key)
            priced.append(staff)
    return priced, queries


def _set(
    extraction: TenderExtraction, cfg: QuickConfig, key: str, value: str, ev: list[VerifiedEvidence]
) -> None:
    option = cfg.questions[key].option(value)
    extraction.choices[key] = FoundValue(value=option.value, label=option.label, evidence=ev)


def _support_hours(
    cfg: QuickConfig, terms: SupportTerms, rules: Staffing, extraction: TenderExtraction
) -> list[UnclearPoint]:
    """Rules 2 and 3 on the support hours: staffed round the clock only for a committed team in
    shifts or on a roster; a call-off team on 24x7, or round-the-clock wording without shifts,
    is on call."""
    lines = [s for s in extraction.staff_lines if s.phase != "build"]
    table = {_norm(s.role): s for s in lines if s.in_price_table}

    def buyer_sets(line: FoundStaffLine) -> bool:
        """Call-off, or a statement about call-off staff in the price table."""
        row = table.get(_norm(line.same_staff_as)) if not line.in_price_table else None
        return line.buyer_sets_headcount or (row is not None and row.buyer_sets_headcount)

    def shifts(line: FoundStaffLine) -> bool:
        return line.count_basis == "per_shift" or any(
            _has(e.quote, terms.staffed) for e in line.evidence
        )

    committed = next(
        (s for s in lines if s.round_the_clock and not buyer_sets(s) and shifts(s)), None
    )
    call_off = next(
        (s for s in lines if buyer_sets(s) and s.round_the_clock),
        None,
    )
    current = extraction.choices.get(SUPPORT_HOURS)
    if committed is not None:
        _set(extraction, cfg, SUPPORT_HOURS, ALWAYS, list(committed.evidence))
        return []
    if call_off is not None:
        _set(extraction, cfg, SUPPORT_HOURS, ON_CALL, list(call_off.evidence))
        return [_query(rules.queries.call_off_hours, call_off, SUPPORT_HOURS, "Support hours")]
    if current is not None and current.value == ALWAYS:
        if not any(_has(e.quote, terms.staffed) for e in current.evidence):
            _set(extraction, cfg, SUPPORT_HOURS, ON_CALL, list(current.evidence))
        return []
    round_the_clock = next((s for s in lines if s.round_the_clock), None)
    if round_the_clock is not None and (current is None or current.value == OFFICE):
        _set(extraction, cfg, SUPPORT_HOURS, ON_CALL, list(round_the_clock.evidence))
    return []


def _desk_sentences(
    terms: SupportTerms, rules: Staffing, docs: list[Document]
) -> Iterator[VerifiedEvidence]:
    """Sentences asking for a helpdesk, service desk or complaint desk (rule 7), outside the
    bidding portal's own helpdesk."""
    for doc in docs:
        for page in doc.page_texts or []:
            number, text = int(page["page"]), str(page["text"])
            for sentence in sentences(text):
                if len(sentence) > terms.max_sentence_chars:
                    continue
                if _has(sentence, terms.ignore):
                    continue
                if _has(sentence, rules.helpdesk_words):
                    yield VerifiedEvidence(
                        page=number,
                        clause_ref=f"Page {number}",
                        quote=sentence,
                        document=doc.filename,
                    )


def _helpdesk(
    cfg: QuickConfig,
    terms: SupportTerms,
    rules: Staffing,
    extraction: TenderExtraction,
    docs: list[Document],
) -> None:
    """Rule 7: a helpdesk team only when the document asks for a helpdesk, a service desk, a
    complaint desk or helpdesk staff; otherwise the usual answer (no helpdesk team)."""
    found = next(_desk_sentences(terms, rules, docs), None)
    if found is None:
        line = next((s for s in extraction.staff_lines if _has(s.role, rules.helpdesk_words)), None)
        found = line.evidence[0] if line is not None else None
    current = extraction.choices.get(HELPDESK)
    if found is not None:
        if current is None or current.value != YES:
            _set(extraction, cfg, HELPDESK, YES, [found])
    elif current is not None and current.value == YES:
        del extraction.choices[HELPDESK]


def _chatbot(cfg: QuickConfig, extraction: TenderExtraction) -> None:
    """Rule 8: complex questions only when the chatbot must connect to the buyer's own
    systems; otherwise the usual answer (common questions)."""
    has_chatbot = CHATBOT in extraction.choices or any(
        f.key == CHATBOT_FEATURE for f in extraction.features
    )
    if not has_chatbot:
        return
    systems = extraction.chatbot_buyer_systems
    current = extraction.choices.get(CHATBOT)
    if systems is not None and systems.evidence:
        _set(extraction, cfg, CHATBOT, ADVANCED, list(systems.evidence))
    elif current is not None and current.value == ADVANCED:
        del extraction.choices[CHATBOT]


def apply_staffing(cfg: QuickConfig, extraction: TenderExtraction, docs: list[Document]) -> None:
    """All the rules, in place, after the support terms are read (merge.apply_code_checks).
    The helpdesk and support-hours rules read the page text, so they apply to every reading;
    the staff and chatbot rules need the staff lines (reads_staff)."""
    rules, terms = cfg.staffing, cfg.support_terms
    if rules is None or terms is None:
        return
    _helpdesk(cfg, terms, rules, extraction, docs)
    queries = _support_hours(cfg, terms, rules, extraction)
    if reads_staff(extraction):
        staff, staff_queries = price_staff(rules, extraction.staff_lines)
        extraction.staffing = staff
        for key in STAFF_NUMBERS:
            extraction.numbers.pop(key, None)
        queries += staff_queries
        _chatbot(cfg, extraction)
    known = {(u.topic, u.quote) for u in extraction.unclear_points}
    extraction.unclear_points += [u for u in queries if (u.topic, u.quote) not in known]

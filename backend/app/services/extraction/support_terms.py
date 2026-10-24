"""Support hours and dedicated support staff a document states, found in code on the page text
(OPEN_QUESTIONS 157): "Provide round-the-clock technical support" answers the support hours,
"Minimum 2 offsite support resources assigned to RailTel" the support staff, each citing its
sentence. Rules and phrases are `support_terms` in quick_estimate.yaml. No LLM is involved, so
a reading made with either reader, or before this check existed, gets the same answers."""

import re
from collections.abc import Iterable, Iterator
from dataclasses import dataclass

from app.services.extraction.basic_reader import NUM, NUMBER_WORDS
from app.services.extraction.client_provided import sentences
from app.services.extraction.tender import VerifiedEvidence
from app.services.quick.config import SupportTerms

RESPONSE_HOURS = re.compile(
    r"\b(?:respon(?:se|d)\w*)\b[^.]{0,60}?\b(\d+(?:\.\d+)?)\s*(?:hours?|hrs?)\b", re.I
)
STAFF_COUNT = re.compile(r"\b" + NUM + r"\b", re.I)


@dataclass
class SupportHours:
    value: str  # a support_hours option value
    evidence: VerifiedEvidence
    # a support sentence saying office or business hours when the answer is round the clock
    conflict: VerifiedEvidence | None = None


def _has(text: str, phrases: Iterable[str]) -> bool:
    return any(re.search(rf"(?<!\w){re.escape(p.lower())}(?!\w)", text) for p in phrases)


def _support_sentences(
    terms: SupportTerms, pages: Iterable[tuple[int, str]], document: str
) -> Iterator[tuple[str, VerifiedEvidence]]:
    """(lower-case sentence, evidence) for each sentence about support, outside the bidding
    portal's own helpdesk, in page order. A label ending in a colon ("Severity 1 support
    tickets:") is read with the sentence after it, as an SLA table row."""
    for number, text in pages:
        label = ""
        for part in sentences(text):
            sentence, label = f"{label} {part}".strip(), ""
            if sentence.endswith(":") and len(sentence) <= terms.max_sentence_chars:
                label = sentence
                continue
            low = sentence.lower()
            if len(sentence) > terms.max_sentence_chars or _has(low, terms.ignore):
                continue
            if _has(low, terms.support_words):
                yield (
                    low,
                    VerifiedEvidence(
                        page=number, clause_ref=f"Page {number}", quote=sentence, document=document
                    ),
                )


def find_support_hours(
    terms: SupportTerms, pages: Iterable[tuple[int, str]], document: str = ""
) -> SupportHours | None:
    """Round the clock (staffed in shifts when the sentence names a staffed desk, else on call)
    over office hours over a fast SLA response; the first sentence of each kind is cited."""
    always: SupportHours | None = None
    office: VerifiedEvidence | None = None
    fast: VerifiedEvidence | None = None
    for low, evidence in _support_sentences(terms, pages, document):
        if _has(low, terms.round_the_clock) and _has(low, terms.office_hours):
            continue  # asks which ("office hours or round the clock?"): answers neither
        if always is None and _has(low, terms.round_the_clock):
            staffed = _has(low, terms.staffed)
            always = SupportHours(terms.values["always" if staffed else "on_call"], evidence)
        elif office is None and _has(low, terms.office_hours):
            office = evidence
        elif fast is None and any(
            float(m.group(1)) < terms.fast_response_hours for m in RESPONSE_HOURS.finditer(low)
        ):
            fast = evidence
    if always is not None:
        always.conflict = office
        return always
    if office is not None:
        return SupportHours(terms.values["office"], office)
    if fast is not None:
        return SupportHours(terms.values["on_call"], fast)
    return None


def find_support_staff(
    terms: SupportTerms, pages: Iterable[tuple[int, str]], document: str = ""
) -> tuple[int, VerifiedEvidence] | None:
    """The first stated number of dedicated support staff: a number followed within three words
    by a staff word, in a support sentence with a `dedicated` word and no `onsite` word."""
    for low, evidence in _support_sentences(terms, pages, document):
        if not _has(low, terms.dedicated) or _has(low, terms.onsite):
            continue
        for m in STAFF_COUNT.finditer(low):
            following = low[m.end(1) : m.end(1) + 60]
            words = re.findall(r"[\w-]+", following)[:4]
            if not any(w in terms.staff_words for w in words):
                continue
            token = m.group(1).replace(",", "")
            count = NUMBER_WORDS.get(token) or (int(float(token)) if token[0].isdigit() else 0)
            if 0 < count <= terms.max_staff:
                return count, evidence
    return None

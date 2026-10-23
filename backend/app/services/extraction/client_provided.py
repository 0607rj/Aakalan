"""Items the client provides (hosting, the web address, the SSL certificate), found in code on
the document's own page text: a sentence such as "Domain and hosting will be provided to the
agency from the department" answers those questions, citing the sentence. Rules (phrases and
items) are `client_provided` in quick_estimate.yaml. No LLM is involved, so a reading made with
either reader, or before this check existed, gets the same answer."""

import re
from collections.abc import Iterable

from app.services.extraction.tender import VerifiedEvidence
from app.services.quick.config import ClientProvided

# sentence ends, and list items that start a new line (bullets, "o ", "1." / "a)"); PDF
# symbol fonts give bullets as private-use characters (U+F0A7, U+F0B7, U+F0D8)
BULLETS = "•▪●◦\\-*"
SENTENCE_BREAK = re.compile(rf"(?<=[.;:!?])\s+|\n\s*(?:[{BULLETS}]|o\s|\w{{1,3}}[.)]\s)")
LEADING_BULLET = re.compile(rf"^[{BULLETS}\s]+")


def _has(text: str, phrases: Iterable[str]) -> bool:
    return any(re.search(rf"\b{re.escape(p.lower())}\b", text) for p in phrases)


def sentences(text: str) -> list[str]:
    """The page's sentences, whitespace collapsed (PDF text breaks lines mid-sentence)."""
    parts = (" ".join(LEADING_BULLET.sub("", part).split()) for part in SENTENCE_BREAK.split(text))
    return [s for s in parts if s]


def find_client_provided(
    rules: ClientProvided, pages: Iterable[tuple[int, str]], document: str = ""
) -> dict[str, tuple[str, VerifiedEvidence]]:
    """{question: (option value, the first sentence that says so)} for each item the client
    provides. A sentence counts when it has a `give` phrase, a `by_client` word and the item's
    word, no `by_vendor` phrase, and is not longer than `max_sentence_chars`."""
    found: dict[str, tuple[str, VerifiedEvidence]] = {}
    for number, text in pages:
        for sentence in sentences(text):
            if len(sentence) > rules.max_sentence_chars:
                continue
            low = sentence.lower()
            if not (_has(low, rules.give) and _has(low, rules.by_client)):
                continue
            if _has(low, rules.by_vendor):
                continue
            for item in rules.items:
                if item.question not in found and _has(low, item.words):
                    evidence = VerifiedEvidence(
                        page=number, clause_ref=f"Page {number}", quote=sentence, document=document
                    )
                    found[item.question] = (item.value, evidence)
    return found

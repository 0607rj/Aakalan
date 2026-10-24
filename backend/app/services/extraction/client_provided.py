"""Items the client provides (hosting, the web address, the SSL certificate), found in code on
the document's own page text: a sentence such as "Domain and hosting will be provided to the
agency from the department" answers those questions, citing the sentence. Rules (phrases and
items) are `client_provided` in quick_estimate.yaml. No LLM is involved, so a reading made with
either reader, or before this check existed, gets the same answer."""

import re
from collections.abc import Iterable

from app.services.extraction.tender import VerifiedEvidence
from app.services.quick.config import ClientProvided, ClientProvidedItem

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


def names_client(rules: ClientProvided, sentence: str) -> bool:
    """The client by its own name: a capitalised name before 's and one of `own_words`
    ("RailTel's cloud"; PDF text may garble the apostrophe), or after one of `by_name`
    ("provisioned by RailTel"), that is not a vendor or a cloud brand (`not_client`)."""
    own = "|".join(re.escape(w) for w in rules.own_words)
    by = "|".join(re.escape(w) for w in rules.by_name)
    names = []
    if own:
        names += re.findall(rf"\b([A-Z][\w&.-]*)[^\w\s]s\s+(?:own\s+)?(?:{own})\b", sentence, re.I)
    if by:
        names += re.findall(rf"\b(?:{by})\s+(?:the\s+)?([A-Z][\w&.-]*)", sentence, re.I)
    blocked = {w.lower() for w in rules.not_client}
    names = [n.rstrip(".-&") for n in names]  # "provisioned by AWS." ends the sentence
    return any(n[:1].isupper() and n.lower() not in blocked for n in names)


def client_provides(rules: ClientProvided, sentence: str) -> list[ClientProvidedItem]:
    """The items a sentence says the client provides: it has a `give` phrase, the client (a
    `by_client` word or its own name), an item's word and no `by_vendor` phrase, and is not
    longer than `max_sentence_chars`."""
    if len(sentence) > rules.max_sentence_chars:
        return []
    low = sentence.lower()
    if not _has(low, rules.give) or _has(low, rules.by_vendor):
        return []
    if not (_has(low, rules.by_client) or names_client(rules, sentence)):
        return []
    return [item for item in rules.items if _has(low, item.words)]


def find_client_provided(
    rules: ClientProvided, pages: Iterable[tuple[int, str]], document: str = ""
) -> dict[str, tuple[str, VerifiedEvidence]]:
    """{question: (option value, the first sentence that says so)} for each item the client
    provides (`client_provides`)."""
    found: dict[str, tuple[str, VerifiedEvidence]] = {}
    for number, text in pages:
        for sentence in sentences(text):
            for item in client_provides(rules, sentence):
                if item.question not in found:
                    evidence = VerifiedEvidence(
                        page=number, clause_ref=f"Page {number}", quote=sentence, document=document
                    )
                    found[item.question] = (item.value, evidence)
    return found

"""Every requirement sentence accounted for (OPEN_QUESTIONS 204).

A reader can skip a requirement. This check, in code, lists the document's requirement
sentences (one of the config's `modal_words`, such as "shall" or "must", and none of its
`skip_words`, the bidder's duties and bid terms) that no finding of the reading quotes. They
are shown on the review screen as "not priced yet", so nothing the document asks for is lost
without the person seeing it. The same pages and reading always give the same list.

A quote covers a sentence when the two share `shared_words` words in a row (all of a shorter
sentence), or the sentence contains all of a shorter quote: a quote may be part of a
sentence, or run across two.
"""

import re
from typing import Any

from app.services.extraction.tender import TenderExtraction, UncoveredSentence
from app.services.quick.config import Coverage

_SPLIT = re.compile(r"(?<=[.;!?])\s+|\n+")
_WORD = re.compile(r"[a-z0-9]+")


def words(text: str) -> list[str]:
    return _WORD.findall(text.lower())


def sentences(text: str) -> list[str]:
    """The page's sentences and lines, spaces tidied."""
    return [" ".join(s.split()) for s in _SPLIT.split(text) if s.strip()]


def _has(phrase_words: list[list[str]], joined: str) -> bool:
    return any(f" {' '.join(p)} " in joined for p in phrase_words if p)


def is_requirement(cfg: Coverage, sentence: str) -> bool:
    """Asks for something (a modal word), is not about the bidder or the bid, and is long
    enough to say what."""
    w = words(sentence)
    if len(w) < cfg.min_sentence_words:
        return False
    joined = f" {' '.join(w)} "
    modal = [words(m) for m in cfg.modal_words]
    skip = [words(s) for s in cfg.skip_words]
    return _has(modal, joined) and not _has(skip, joined)


def _quotes(value: Any) -> list[str]:
    """Every quote in the reading (features, scope, extras, answers, numbers, staff...)."""
    if isinstance(value, dict):
        out = [str(value["quote"])] if isinstance(value.get("quote"), str) else []
        for v in value.values():
            out += _quotes(v)
        return out
    if isinstance(value, list):
        return [q for v in value for q in _quotes(v)]
    return []


Grams = dict[int, set[tuple[str, ...]]]


def _grams(quotes: list[str], sizes: range, shared: int) -> tuple[Grams, Grams]:
    """Every run of each size in the quotes, and the whole of each quote shorter than
    `shared` (such a quote covers a sentence that contains all of it)."""
    runs: Grams = {n: set() for n in sizes}
    short: Grams = {n: set() for n in sizes}
    for q in quotes:
        w = words(q)
        for n in sizes:
            runs[n].update(tuple(w[i : i + n]) for i in range(len(w) - n + 1))
        if len(w) in short and len(w) < shared:
            short[len(w)].add(tuple(w))
    return runs, short


def _covered(w: list[str], runs: Grams, short: Grams, shared: int) -> bool:
    n = min(shared, len(w))
    if any(tuple(w[i : i + n]) in runs[n] for i in range(len(w) - n + 1)):
        return True
    return any(
        tuple(w[i : i + m]) in short[m] for m in short for i in range(len(w) - m + 1) if short[m]
    )


def find_uncovered(
    cfg: Coverage, extraction: TenderExtraction, docs: list[tuple[str, list[tuple[int, str]]]]
) -> tuple[list[UncoveredSentence], int]:
    """The requirement sentences no quote covers, in document and page order: the first
    `max_listed`, and how many more there are."""
    sizes = range(cfg.min_sentence_words, cfg.shared_words + 1)
    runs, short = _grams(_quotes(extraction.model_dump(mode="json")), sizes, cfg.shared_words)
    found: list[UncoveredSentence] = []
    seen: set[str] = set()
    for document, pages in docs:
        for page, text in pages:
            for sentence in sentences(text):
                if not is_requirement(cfg, sentence):
                    continue
                w = words(sentence)
                if _covered(w, runs, short, cfg.shared_words):
                    continue
                key = " ".join(w)
                if key in seen:
                    continue
                seen.add(key)
                found.append(UncoveredSentence(page=page, text=sentence[:400], document=document))
    return found[: cfg.max_listed], max(0, len(found) - cfg.max_listed)

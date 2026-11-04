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


def unmatched_parts(
    cfg: Coverage, extraction: TenderExtraction, text: str, more: list[str]
) -> list[str]:
    """A typed description has no "shall": every part asks for something (OPEN_QUESTIONS
    210). Its parts, split at punctuation and `description_split_words`, of at least
    `description_min_words` words, that nothing in the reading accounts for, in order, each
    once, at most `max_listed`. A feature's or extra's quote accounts for one part only: of the
    parts it covers, the one sharing most words with the feature's name (a quote running over
    two asks, "pay fees online and see their child's attendance", is one finding, not two).
    Other quotes (answers, add-ons, numbers) and `more` (e.g. the clauses that rule a feature
    out) account for every part they cover. A part whose words are only generic ones
    (`description_generic_words`) and the industry's ("A school system") names the software and
    is not listed."""
    if not cfg.description_split_words:
        return []
    joiners = "|".join(r"\s+".join(map(re.escape, w.split())) for w in cfg.description_split_words)
    pieces = re.split(rf"[.;,!?:\n]|\b(?:{joiners})\b", text, flags=re.IGNORECASE)
    parts = [(" ".join(p.split()), words(p)) for p in pieces]
    parts = [(p, w) for p, w in parts if len(w) >= cfg.description_min_words]
    sizes = range(1, cfg.shared_words + 1)
    dump = extraction.model_dump(mode="json")
    found = {"features", "other_features"}
    plain = [*_quotes({k: v for k, v in dump.items() if k not in found}), *more]
    runs, short = _grams(plain, sizes, cfg.shared_words)
    done = {i for i, (_, w) in enumerate(parts) if _covered(w, runs, short, cfg.shared_words)}
    named = [(f.label, f.evidence) for f in extraction.features]
    named += [(f"{o.name} {o.description}", o.evidence) for o in extraction.other_features]
    m = cfg.description_min_words
    for name, evidence in named:
        label = {_stem(x) for x in words(name)}
        for ev in evidence:
            q = words(ev.quote)
            q_runs = {tuple(q[i : i + m]) for i in range(len(q) - m + 1)}
            # a part the quote shares `m` words in a row with (or all of a shorter quote)
            touched = [
                i
                for i, (_, w) in enumerate(parts)
                if any(tuple(w[j : j + m]) in q_runs for j in range(len(w) - m + 1))
                or (len(q) < m and _covered(w, *_grams([ev.quote], sizes, cfg.shared_words), m))
            ]
            if touched:  # the part most like the feature's name, then one not yet claimed
                done.add(
                    max(
                        touched,
                        key=lambda i: (
                            len(label & set(map(_stem, parts[i][1]))),
                            i not in done,
                            -i,
                        ),
                    )
                )
    generic = {_stem(x) for g in cfg.description_generic_words for x in words(g)}
    generic |= {_stem(x) for x in words(extraction.project_domain)}
    out: list[str] = []
    seen: set[str] = set()
    for i, (part, w) in enumerate(parts):
        key = " ".join(w)
        if i in done or key in seen or {_stem(x) for x in w} <= generic:
            continue
        seen.add(key)
        out.append(part[:200])
    return out[: cfg.max_listed]


def _stem(word: str) -> str:
    """A word without a plural "s" ("meetings" and "meeting" match)."""
    return word[:-1] if len(word) > 3 and word.endswith("s") else word


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

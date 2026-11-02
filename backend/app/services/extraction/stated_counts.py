"""Counts a document states for what is built (OPEN_QUESTIONS 194): "rolled out in phases up to
200 services" or "API based integration with 20 State Systems" make that feature several
modules (`story_units`), citing the line. Found in code on the page text, with strict rules
(`stated_counts` in quick_estimate.yaml), so a table's item number ("69 Reports need to be
customizable") or a section number ("5.2 Banking Use Cases") is never read as a count. The
person checks every count on the review form with its quote beside it. No LLM is involved."""

import math
import re
from collections.abc import Iterable
from dataclasses import dataclass

from app.services.extraction.tender import VerifiedEvidence
from app.services.quick.config import StatedCountRule, StatedCounts


@dataclass(frozen=True)
class StatedCount:
    feature: str
    count: int
    units: int
    level: str
    evidence: VerifiedEvidence


def _words(phrases: Iterable[str]) -> str:
    return "|".join(re.escape(p.lower()) for p in sorted(phrases, key=len, reverse=True))


def _pattern(rule: StatedCountRule) -> re.Pattern[str]:
    """[after phrase] NUMBER [up to two allowed words] NOUN, as whole words. The number may not
    follow a letter, digit or punctuation mark that makes it part of a longer number or a
    section number ("5.2", "F1.36", "1,000")."""
    after = rf"(?:\b(?:{_words(rule.after)})\s+)" if rule.after else ""
    adjectives = rf"(?:(?:{_words(rule.adjectives)})\s+){{0,2}}" if rule.adjectives else ""
    return re.compile(
        rf"{after}(?<![\w.,/-])(\d{{1,4}})\s+{adjectives}(?:{_words(rule.nouns)})\b", re.I
    )


def counts_in_line(rules: StatedCounts, rule: StatedCountRule, line: str) -> list[int]:
    """The counts one line states for the rule. A count at the very start of the line (a
    numbered table row) counts only when the line is no longer than
    `max_line_words_at_start` words (a table cell such as "200 services"), and only for a rule
    without `after` phrases."""
    text = " ".join(line.split())
    found = []
    for match in _pattern(rule).finditer(text):
        count = int(match.group(1))
        if not 1 <= count <= rules.max_count:
            continue
        at_start = match.start(1) == 0
        if at_start and len(text.split()) > rules.max_line_words_at_start:
            continue
        found.append(count)
    return found


def find_stated_counts(
    rules: StatedCounts, pages: Iterable[tuple[int, str]], document: str = "", max_units: int = 1
) -> dict[str, StatedCount]:
    """{feature: the largest count stated for it, as modules}, units =
    min(max_units, ceil(count / per_unit)), citing the first line with that count."""
    best: dict[str, StatedCount] = {}
    for number, text in pages:
        for line in text.splitlines():
            for rule in rules.rules:
                for count in counts_in_line(rules, rule, line):
                    current = best.get(rule.feature)
                    if current is not None and current.count >= count:
                        continue
                    units = min(max_units, math.ceil(count / rule.per_unit))
                    quote = " ".join(line.split())
                    evidence = VerifiedEvidence(
                        page=number, clause_ref=f"Page {number}", quote=quote, document=document
                    )
                    level = rule.level
                    best[rule.feature] = StatedCount(rule.feature, count, units, level, evidence)
    return best

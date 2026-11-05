"""The uptime a document asks for, found in code on the page text (OPEN_QUESTIONS 219).

An SLA's penalty table states the uptime by where penalties start: "100% available ... <99.5%
& >= 0.5% ... < 99% & >= 1%" asks for 99.5% (below it the first penalty applies). A sentence
can also state it ("99.9% uptime", "availability of at least 99.5%"). Only a percentage near
an availability word (`words`, within `window_chars` before it) counts, and only between
`min_percent` and 100 (exclusive), so "<5% of the 0.5%" or "100% available" is never one.
The highest such figure is the uptime asked for; it answers the downtime question with the
lowest option that meets it, citing the line. No LLM is involved.
"""

import re
from dataclasses import dataclass
from decimal import Decimal

from app.services.extraction.tender import VerifiedEvidence
from app.services.quick.config import UptimeTerms

PERCENT = r"(\d{2}(?:\.\d{1,3})?)\s*%"
# "< 99.5%", "below 99.5 %", "less than 99.5%": the penalty threshold
THRESHOLD = re.compile(r"(?:<\s*|\b(?:below|less\s+than|under)\s+)" + PERCENT, re.I)
# "99.9% uptime", "99.5% availability", "uptime of (at least) 99.9%"
STATED = re.compile(
    PERCENT + r"\s+(?:uptime|up-time|availability)\b"
    r"|\b(?:uptime|up-time|availability)\s+(?:of\s+)?(?:at\s+least\s+|minimum\s+(?:of\s+)?)?"
    + PERCENT,
    re.I,
)


@dataclass(frozen=True)
class UptimeAsked:
    percent: Decimal
    evidence: VerifiedEvidence


def _line(text: str, pos: int) -> str:
    start = text.rfind("\n", 0, pos) + 1
    end = text.find("\n", pos)
    return text[start : end if end >= 0 else len(text)].strip()


def find_uptime(
    cfg: UptimeTerms, pages: list[tuple[int, str]], document: str = ""
) -> UptimeAsked | None:
    """The highest uptime the pages ask for, with the line that states it (None: none)."""
    near = re.compile("|".join(re.escape(w) for w in cfg.words), re.I)
    best: UptimeAsked | None = None
    for page, text in pages:
        for pattern in (THRESHOLD, STATED):
            for m in pattern.finditer(text):
                value = next(g for g in m.groups() if g is not None)
                percent = Decimal(value)
                if not cfg.min_percent <= percent < 100:
                    continue
                if near.search(text, max(0, m.start() - cfg.window_chars), m.end()) is None:
                    continue
                if best is None or percent > best.percent:
                    quote = _line(text, m.start())
                    evidence = VerifiedEvidence(
                        page=page, clause_ref="", quote=quote, document=document
                    )
                    best = UptimeAsked(percent=percent, evidence=evidence)
    return best

"""Pre-bid queries (brief Section 9, step 6): one drafted query per vague clause the reader
flagged, plus one per key fact the tender leaves out. Text only; nothing here is priced."""

from typing import Literal

from pydantic import BaseModel

from app.services.extraction.tender import TenderExtraction
from app.services.quick.config import QuickConfig

CHOICE_FIELDS = frozenset({"availability", "hosting", "support_hours"})
CHATBOT_FIELD = "chatbot_queries_per_day"
CHATBOT_FEATURE = "ai_chatbot"


class PrebidQuery(BaseModel):
    number: int
    kind: Literal["unclear", "missing"]
    topic: str
    clause_ref: str
    page: int | None
    quote: str
    query: str


def prebid_queries(cfg: QuickConfig, extraction: TenderExtraction) -> list[PrebidQuery]:
    items: list[PrebidQuery] = []

    def add(**fields: object) -> None:
        items.append(PrebidQuery.model_validate({"number": len(items) + 1, **fields}))

    for u in extraction.unclear_points:
        query = u.prebid_query
        if not query and u.quote and u.page is not None:
            query = cfg.prebid.vague_query.format(
                clause=u.clause_ref or "(unnumbered)", page=u.page, quote=u.quote
            )
        if query:
            add(
                kind="unclear",
                topic=u.topic,
                clause_ref=u.clause_ref,
                page=u.page,
                quote=u.quote,
                query=query,
            )

    features = {f.key for f in extraction.features}
    for field, text in cfg.prebid.missing.items():
        if field in CHOICE_FIELDS:
            missing = field not in extraction.choices
        elif field == CHATBOT_FIELD:
            missing = CHATBOT_FEATURE in features and field not in extraction.numbers
        else:
            missing = field not in extraction.numbers
        if missing:
            topic = field.replace("_", " ").capitalize() + " not stated"
            add(kind="missing", topic=topic, clause_ref="", page=None, quote="", query=text)
    return items

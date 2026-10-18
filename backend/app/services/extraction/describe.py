"""Suggest features from a few lines the user types about the software ("a clinic app where
patients book appointments and pay online"). The text is read like a one-page requirement
document: by the AI reader when a key is configured (rule 7: fenced as data; rule 1: it only
suggests), else by the keyword reader. Every suggestion must quote the user's own words, and
nothing is priced until the user confirms the ticks (rule 6). Nothing is stored."""

import logging

from pydantic import BaseModel

from app.llm.client import LLMClient, LLMNotConfiguredError, LLMRefusedError, get_llm_client
from app.services.documents.parsing import Page, ParsedDocument
from app.services.extraction.basic_reader import basic_read
from app.services.extraction.tender import (
    BASIC_READER_VERSION,
    PROMPT_VERSION,
    FoundOtherFeature,
    TenderExtraction,
    ai_read,
    verify_findings,
)
from app.services.quick.config import QuickConfig

log = logging.getLogger(__name__)
DESCRIPTION = "Your description"


class SuggestedFeature(BaseModel):
    key: str
    label: str
    quote: str  # the user's words that asked for it


class Suggestion(BaseModel):
    reader: str  # "ai" | "basic"
    features: list[SuggestedFeature]
    other_features: list[FoundOtherFeature]  # not in the list: added as the user's own features
    choices: dict[str, str | int]  # question answers the text gives (e.g. a mobile app)
    note: str | None  # e.g. why the basic reader may miss things


def suggest_features(cfg: QuickConfig, text: str) -> Suggestion:
    parsed = ParsedDocument(kind="text", pages=[Page(1, text)], approximate_pages=False)
    llm: LLMClient | None
    try:
        llm = get_llm_client()
    except LLMNotConfiguredError:
        llm = None
    note = None
    if llm is not None:
        try:
            raw, reader, version = ai_read(llm, cfg, parsed).output, "ai", PROMPT_VERSION
        except LLMRefusedError:
            raw = None
        except Exception:  # network / API errors: fall back to the keyword reader
            log.exception("description reading failed")
            raw = None
        if raw is None:
            note = "The AI could not read this just now, so we matched keywords instead."
    if llm is None or raw is None:
        raw, reader, version = basic_read(cfg, parsed), "basic", BASIC_READER_VERSION
        note = note or (
            "Matched by keywords (no AI key set), so some features may be missed: "
            "please tick anything else you need."
        )
    found: TenderExtraction = verify_findings(
        cfg, parsed, raw, reader=reader, version=version, document=DESCRIPTION
    )
    return Suggestion(
        reader=reader,
        features=[
            SuggestedFeature(key=f.key, label=f.label, quote=f.evidence[0].quote)
            for f in found.features
            if f.evidence
        ],
        other_features=found.other_features,
        choices={k: v.value for k, v in found.choices.items()},
        note=note,
    )

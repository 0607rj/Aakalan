"""Suggest features from a few lines the user types about the software ("a clinic app where
patients book appointments and pay online"). The text is read like a one-page requirement
document: by the AI reader when a key is configured (rule 7: fenced as data; rule 1: it only
suggests), else by the keyword reader. Every suggestion must quote the user's own words, and
nothing is priced until the user confirms the ticks (rule 6). The AI's reading is kept per
organisation by a fingerprint of the text (never the text), so the same words give the same
features every time (OPEN_QUESTIONS 181); nothing else is stored."""

import hashlib
import logging
import re

from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.tenancy import scoped
from app.llm.client import LLMClient, LLMNotConfiguredError, LLMRefusedError, get_llm_client
from app.models import DescriptionReading
from app.services.documents.parsing import Page, ParsedDocument
from app.services.extraction.basic_reader import basic_read
from app.services.extraction.tender import (
    BASIC_READER_VERSION,
    PROMPT_VERSION,
    ExtractionOutput,
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


class SuggestedScope(BaseModel):
    key: str
    label: str
    quote: str  # the user's words that suggested it
    status: str  # explicit (asked for) / inferred (probably needed: please check)


class Suggestion(BaseModel):
    reader: str  # "ai" | "basic"
    features: list[SuggestedFeature]
    other_features: list[FoundOtherFeature]  # not in the list: added as the user's own features
    choices: dict[str, str | int]  # question answers the text gives (e.g. a mobile app)
    scope: list[SuggestedScope] = []  # scope items the words ask for (e.g. two-step sign-in)
    not_priced: list[str] = []  # asked for, but not something this estimate can price
    note: str | None  # e.g. why the basic reader may miss things
    # ruled out by the words ("no mobile app"): offered as "Not included", with the words
    excluded: list[SuggestedFeature] = []
    excluded_scope: list[SuggestedScope] = []


def with_everyday_words(cfg: QuickConfig) -> QuickConfig:
    """The keyword lists plus the everyday words people use in a short description."""
    extra = cfg.keywords.description_features
    if not extra:
        return cfg
    words = {
        key: [*cfg.keywords.features.get(key, []), *extra.get(key, [])]
        for key in {*cfg.keywords.features, *extra}
    }
    keywords = cfg.keywords.model_copy(update={"features": words})
    return cfg.model_copy(update={"keywords": keywords})


CLAUSE = re.compile(r"[.;,!?\n]|\bbut\b", re.IGNORECASE)
WORD = re.compile(r"[a-z0-9']+")


def _tokens(text: str) -> list[str]:
    return WORD.findall(text.lower().replace("\u2019", "'"))


def _at(tokens: list[str], phrase: list[str]) -> list[int]:
    """Where `phrase` (tokens) starts in `tokens`."""
    n = len(phrase)
    return [i for i in range(len(tokens) - n + 1) if n and tokens[i : i + n] == phrase]


def _negated(cfg: QuickConfig, tokens: list[str], start: int, end: int) -> bool:
    """An exclusion phrase just before tokens[start:end] or just after them (at most
    `exclusion_window_words` words between)."""
    kw = cfg.keywords
    gap = kw.exclusion_window_words
    for phrase in kw.exclusion_before:
        pt = _tokens(phrase)
        if any(0 <= start - (j + len(pt)) <= gap for j in _at(tokens, pt)):
            return True
    for phrase in kw.exclusion_after:
        pt = _tokens(phrase)
        if any(0 <= j - end <= gap for j in _at(tokens, pt)):
            return True
    return False


def ruled_out(cfg: QuickConfig, text: str) -> dict[str, str]:
    """Features the description rules out ("no mobile app", "don't need online payments",
    "payments not needed"), with the clause that says so: the feature's words appear only in
    clauses that negate them (a clause that asks for it wins). Code only, no AI."""
    words = with_everyday_words(cfg).keywords.features
    negated: dict[str, str] = {}
    wanted: set[str] = set()
    for clause in CLAUSE.split(text):
        tokens = _tokens(clause)
        for key, phrases in words.items():
            for phrase in phrases:
                pt = _tokens(phrase)
                for i in _at(tokens, pt):
                    if _negated(cfg, tokens, i, i + len(pt)):
                        negated.setdefault(key, clause.strip())
                    else:
                        wanted.add(key)
    return {k: q for k, q in negated.items() if k not in wanted}


def _remembered(
    db: Session, org_id: str, llm: LLMClient, cfg: QuickConfig, parsed: ParsedDocument, text: str
) -> ExtractionOutput:
    """The AI's reading of this exact text for the organisation: the kept one, else a new one,
    kept (OPEN_QUESTIONS 181). The same words then give the same features on every click."""
    key = {
        "text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "prompt_version": PROMPT_VERSION,
        "model": get_settings().llm_model,
    }
    query = scoped(DescriptionReading, org_id).filter_by(**key)
    kept = db.scalars(query).first()
    if kept is not None:
        return ExtractionOutput.model_validate(kept.output)
    output = ai_read(llm, cfg, parsed).output
    db.add(DescriptionReading(org_id=org_id, output=output.model_dump(mode="json"), **key))
    try:
        db.commit()
    except IntegrityError:  # the same text read twice at once: keep the first
        db.rollback()
        kept = db.scalars(query).first()
        if kept is not None:
            return ExtractionOutput.model_validate(kept.output)
    return output


def suggest_features(
    cfg: QuickConfig, text: str, db: Session | None = None, org_id: str | None = None
) -> Suggestion:
    """`db` and `org_id`: keep the AI's reading for the organisation (same words, same
    features); without them every call reads afresh."""
    parsed = ParsedDocument(kind="text", pages=[Page(1, text)], approximate_pages=False)
    llm: LLMClient | None
    try:
        llm = get_llm_client()
    except LLMNotConfiguredError:
        llm = None
    note = None
    if llm is not None:
        try:
            raw = (
                _remembered(db, org_id, llm, cfg, parsed, text)
                if db is not None and org_id is not None
                else ai_read(llm, cfg, parsed).output
            )
            reader, version = "ai", PROMPT_VERSION
        except LLMRefusedError:
            raw = None
        except Exception:  # network / API errors: fall back to the keyword reader
            log.exception("description reading failed")
            raw = None
        if raw is None:
            note = "The AI could not read this just now, so we matched keywords instead."
    if llm is None or raw is None:
        raw, reader, version = (
            basic_read(with_everyday_words(cfg), parsed),
            "basic",
            BASIC_READER_VERSION,
        )
        note = note or (
            "Matched by keywords (no AI key set), so some features may be missed: "
            "please tick anything else you need."
        )
    found: TenderExtraction = verify_findings(
        cfg, parsed, raw, reader=reader, version=version, document=DESCRIPTION
    )
    excluded = ruled_out(cfg, text)
    return Suggestion(
        reader=reader,
        features=[
            SuggestedFeature(key=f.key, label=f.label, quote=f.evidence[0].quote)
            for f in found.features
            if f.evidence and f.key not in excluded
        ],
        excluded=[
            SuggestedFeature(key=k, label=cfg.feature(k).label, quote=q)
            for k, q in excluded.items()
        ],
        excluded_scope=[
            SuggestedScope(key=sc.key, label=sc.label, quote=sc.evidence[0].quote, status=sc.status)
            for sc in found.scope_set_aside
            if sc.evidence and sc.status == "excluded"
        ],
        other_features=found.other_features,
        choices={k: v.value for k, v in found.choices.items()},
        scope=[
            SuggestedScope(key=sc.key, label=sc.label, quote=sc.evidence[0].quote, status=sc.status)
            for sc in found.scope
            if sc.evidence
        ],
        not_priced=[n.label for n in found.not_priced],
        note=note,
    )

"""Research a feature the catalog lacks: look in the catalog first (published blocks and the
organisation's researched ones); else ask the AI for pages that state hours for it, open each
page and keep a figure only if it is really there, and derive the hours from the kept figures;
else let the AI analyse the feature as a combination of catalog blocks at a level, with the
hours taken from those blocks. Either way the block is saved for the organisation (approved
automatically) and reused. The AI never gives a number (rule 1): it points at pages or picks
blocks; the figures come from the pages or the catalog and the arithmetic is here. Without an
AI key nothing is searched and the custom feature type prices the feature as before."""

import logging
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from functools import lru_cache
from statistics import median
from typing import Literal

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.tenancy import scoped
from app.llm.client import LLMNotConfiguredError, LLMRefusedError, get_llm_client, load_prompt
from app.models import ResearchedComponent, User
from app.services.engine import reference as ref
from app.services.engine.reference import BaselineEra, Size
from app.services.estimates.reference_store import catalog_for
from app.services.quick.config import QuickConfig, Research
from app.services.research import library
from app.services.research.fetch import FetchError, get_page_fetcher
from app.services.seeding.reference import load_reference

log = logging.getLogger(__name__)

PREFIX = "researched_"
TENTH = Decimal("0.1")
SIZES = [Size.S, Size.M, Size.L]
STOPWORDS = frozenset(
    [
        "and",
        "or",
        "the",
        "for",
        "with",
        "from",
        "into",
        "of",
        "to",
        "a",
        "an",
        "in",
        "on",
        "by",
        "as",
        "at",
        "is",
        "be",
        "via",
        "per",
        "using",
        "our",
        "your",
        "their",
        "app",
        "apps",
        "feature",
        "features",
        "module",
        "system",
    ]
)


class FoundSource(BaseModel):
    """One page the AI points at, with the figure it says the page states."""

    url: str = Field(max_length=2000)
    publisher: str = Field(default="", max_length=200)
    title: str = Field(default="", max_length=300)
    year: int | None = None
    label: str = Field(max_length=200)
    quote: str = Field(max_length=600)
    low: Decimal = Field(gt=0)
    high: Decimal | None = Field(default=None, gt=0)
    unit: Literal["hours", "days"] = "hours"
    scope: Literal["dev-only", "whole-team", "unclear"] = "unclear"


class ResearchReply(BaseModel):
    section: str = Field(max_length=40)
    description: str = Field(default="", max_length=400)
    sources: list[FoundSource] = []


class Part(BaseModel):
    block: str = Field(max_length=100)
    level: Literal["basic", "standard", "advanced"]
    why: str = Field(default="", max_length=300)


class AnalysisReply(BaseModel):
    """The AI's analysis: the feature as catalog blocks at a level (no numbers)."""

    section: str = Field(max_length=40)
    description: str = Field(default="", max_length=400)
    parts: list[Part] = []


class CheckedSource(BaseModel):
    """A source after the code opened its page: kept (`ok`) or why not."""

    url: str
    publisher: str
    title: str
    year: int | None
    label: str
    quote: str
    hours: list[Decimal]  # the stated figures in hours (days x hours per day)
    scope: str
    ok: bool
    reason: str = ""


class Researched(BaseModel):
    """The outcome of one search, before it is saved."""

    reply: ResearchReply | None
    checked: list[CheckedSource] = []
    analysis: AnalysisReply | None = None  # used when too few web sources checked out
    model: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    error: str = ""


# --- matching ------------------------------------------------------------------------------


def _words(text: str) -> set[str]:
    out = set()
    for w in re.findall(r"[a-z0-9]+", text.lower()):
        if len(w) < 3 or w in STOPWORDS:
            continue
        out.add(w[:-1] if len(w) > 3 and w.endswith("s") else w)
    return out


def match_share(feature: str, block_name: str) -> Decimal:
    """Share of the feature's words that the block's name contains."""
    want = _words(feature)
    if not want:
        return Decimal(0)
    return Decimal(len(want & _words(block_name))) / Decimal(len(want))


def find_block(
    name: str, components: list[ref.CatalogComponent], threshold: Decimal
) -> ref.CatalogComponent | None:
    """The catalog block that best matches a feature by name, if close enough. Generic custom
    blocks ("Custom AI feature") never match: they are the fallback, not an answer."""
    best: tuple[Decimal, ref.CatalogComponent] | None = None
    for c in components:
        if c.category == "custom" and not c.key.startswith(PREFIX):
            continue
        share = match_share(name, c.name)
        if share >= threshold and (best is None or share > best[0]):
            best = (share, c)
    return best[1] if best else None


# --- web sources ---------------------------------------------------------------------------


def normalise(text: str) -> str:
    text = text.lower().replace("–", "-").replace("—", "-").replace(" ", " ")
    text = re.sub(r"(?<=\d),(?=\d{3}\b)", "", text)  # 1,200 -> 1200
    return re.sub(r"\s+", " ", text).strip()


def _number(value: Decimal) -> str:
    return format(value.normalize(), "f")


def _occurrences(n: str, text: str) -> list[re.Match[str]]:
    return list(re.finditer(rf"(?<![\d.]){re.escape(n)}(?![\d.])", text))


def check_source(src: FoundSource, page: str, window: int) -> str:
    """'' when the stated figure is on the page near the feature's name, else why not."""
    text = normalise(page)
    numbers = [_number(n) for n in (src.low, src.high) if n is not None]
    for n in numbers:
        if not _occurrences(n, text):
            return f"{n} is not on the page"
    if normalise(src.quote) in text:
        return ""
    label = _words(src.label)
    for n in numbers:
        for m in _occurrences(n, text):
            near = text[max(0, m.start() - window) : m.end() + window]
            if label and label <= _words(near):
                return ""
    return "the figure is not next to the feature's name on the page"


def _hours(src: FoundSource, hours_per_day: int) -> list[Decimal]:
    factor = Decimal(hours_per_day) if src.unit == "days" else Decimal(1)
    return [n * factor for n in (src.low, src.high) if n is not None]


def check_sources(
    sources: list[FoundSource], research: Research, hours_per_day: int
) -> list[CheckedSource]:
    fetch = get_page_fetcher()
    out = []
    for src in sources[: research.max_sources]:
        hours = _hours(src, hours_per_day)
        reason = ""
        if any(not research.min_hours <= h <= research.max_hours for h in hours):
            reason = "the figure is outside the believable range"
        else:
            try:
                page = fetch(src.url, research.fetch_timeout_seconds, research.fetch_max_bytes)
                reason = check_source(src, page, research.quote_window_chars)
            except FetchError as exc:
                reason = f"page could not be opened ({exc})"
        out.append(
            CheckedSource(
                url=src.url,
                publisher=src.publisher,
                title=src.title,
                year=src.year,
                label=src.label,
                quote=src.quote,
                hours=hours,
                scope=src.scope,
                ok=not reason,
                reason=reason,
            )
        )
    return out


def derive_effort(hours: list[Decimal], factor: Decimal, hours_per_day: int) -> dict[Size, Decimal]:
    """S / M / L person-days = lowest / median / highest kept figure x factor / hours per day
    (the catalog v5 method), rounded half-up to 0.1 day (at least 0.1)."""

    def pd(h: Decimal) -> Decimal:
        days = (h * factor / Decimal(hours_per_day)).quantize(TENTH, rounding=ROUND_HALF_UP)
        return max(days, TENTH)

    return {Size.S: pd(min(hours)), Size.M: pd(Decimal(median(hours))), Size.L: pd(max(hours))}


# --- AI analysis: the feature as catalog blocks ---------------------------------------------


def _step(size: Size, by: int) -> Size:
    return SIZES[min(max(SIZES.index(size) + by, 0), len(SIZES) - 1)]


def standard_blocks(cfg: QuickConfig) -> set[str]:
    """Blocks every project of some size already has (never part of an analysis)."""
    return {k for t in cfg.sizing.tiers for k in t.base_components}


def valid_parts(parts: list[Part], catalog: ref.Catalog, standard: set[str]) -> list[Part]:
    """Parts naming a published, non-generic block that is not already in every project."""
    keys = {c.key: c for c in catalog.components}
    out: list[Part] = []
    seen: set[str] = set()
    for part in parts:
        c = keys.get(part.block)
        if c is None or part.block in standard or part.block in seen:
            continue
        if c.category == "custom" or part.block.startswith(PREFIX):
            continue
        seen.add(part.block)
        out.append(part)
    return out


def composed_effort(
    parts: list[Part], catalog: ref.Catalog, level_size: dict[str, Size]
) -> dict[Size, Decimal]:
    """M = the parts' person-days at the levels the analysis chose; S and L = the same parts one
    size smaller / larger (S and L of a block are the floor and ceiling). Catalog numbers only."""
    out = {}
    for shift, size in ((-1, Size.S), (0, Size.M), (1, Size.L)):
        out[size] = sum(
            (catalog.get(p.block).base_effort_pd[_step(level_size[p.level], shift)] for p in parts),
            Decimal(0),
        )
    return out


def analyse(
    cfg: QuickConfig, name: str, catalog: ref.Catalog, standard: set[str]
) -> tuple[AnalysisReply | None, str, int, int, str]:
    """The AI's analysis of the feature as catalog blocks (only block names and descriptions
    are sent, never hours)."""
    research = cfg.research
    assert research is not None
    blocks = "\n".join(
        f"- {c.key}: {c.name} - {c.description}"
        for c in catalog.components
        if c.category != "custom" and not c.key.startswith(PREFIX)
    )
    system = (
        load_prompt(f"{research.analyse_prompt}.md")
        .replace("{{sections}}", ", ".join(catalog_sections()))
        .replace("{{blocks}}", blocks)
        .replace("{{standard}}", ", ".join(sorted(standard)))
    )
    try:
        result = get_llm_client().extract(
            system=system, user=f"Feature: {name[:200]}", schema=AnalysisReply
        )
    except (LLMNotConfiguredError, LLMRefusedError) as exc:
        return None, "", 0, 0, str(exc)
    return result.output, result.model, result.input_tokens, result.output_tokens, ""


# --- building the block --------------------------------------------------------------------


def slug(name: str) -> str:
    return PREFIX + "_".join(sorted(_words(name)))[:80]


@lru_cache
def catalog_sections() -> dict[str, str]:
    return load_reference(get_settings().seeds_dir).catalog.sections


def _section(wanted: str, base: ref.CatalogComponent) -> str:
    return wanted if wanted in catalog_sections() else (base.section or "custom")


def build_component(
    key: str,
    name: str,
    reply: ResearchReply,
    kept: list[CheckedSource],
    base: ref.CatalogComponent,
    research: Research,
    hours_per_day: int,
) -> ref.CatalogComponent:
    """From web sources: the generic block of the feature's type (bucket, task mix, drivers)
    with hours and evidence from the kept sources."""
    hours = [h for s in kept for h in s.hours]
    effort = derive_effort(hours, research.feature_level_factor, hours_per_day)
    figures = " / ".join(
        _number(h) for h in sorted({min(hours), Decimal(median(hours)), max(hours)})
    )
    cites = "; ".join(f"{s.publisher or s.url} {s.label}" for s in kept)
    today = datetime.now(UTC).date().isoformat()
    evidence = [
        ref.EffortEvidence(
            id=f"{key}.{n}",
            citation=f"{s.publisher}, '{s.title}': {s.label}: \"{s.quote}\" (web research, "
            f"checked on the page {today})",
            source_type="vendor_estimate",
            published=s.year,
            url=s.url,
            era=BaselineEra.UNKNOWN,
            era_basis=ref.EraBasis.NOT_ESTABLISHED,
            quality="low",
        )
        for n, s in enumerate(kept, start=1)
    ]
    return base.model_copy(
        update={
            "key": key,
            "name": name[:200],
            "section": _section(reply.section, base),
            "description": reply.description or f"Researched from the web: {name}",
            "base_effort_pd": effort,
            "source": f"{figures} team hours (lowest / median / highest checked figure) x "
            f"{research.feature_level_factor} / {hours_per_day} h per day; low confidence; "
            f"web research: {cites}",
            "source_era": BaselineEra.UNKNOWN,
            "era_reason": "Web sources; none states whether AI coding tools were used",
            "confidence": "low",
            "evidence": evidence,
        }
    )


def build_composed(
    key: str,
    name: str,
    analysis: AnalysisReply,
    parts: list[Part],
    catalog: ref.Catalog,
    base: ref.CatalogComponent,
    level_size: dict[str, Size],
) -> ref.CatalogComponent:
    """From the AI analysis: the generic block of the feature's type with the parts' hours."""
    effort = composed_effort(parts, catalog, level_size)
    recipe = ", ".join(f"{catalog.get(p.block).name} ({p.level})" for p in parts)
    today = datetime.now(UTC).date().isoformat()
    return base.model_copy(
        update={
            "key": key,
            "name": name[:200],
            "section": _section(analysis.section, base),
            "description": analysis.description or f"Analysed by AI: {name}",
            "base_effort_pd": effort,
            "source": f"AI analysis (no published hours found): {recipe}; hours are those "
            "blocks' own catalog hours (S / L = one size smaller / larger); low confidence",
            "source_era": BaselineEra.UNKNOWN,
            "era_reason": "Composed from catalog blocks; AI use behind their hours is not "
            "established",
            "confidence": "low",
            "evidence": [
                ref.EffortEvidence(
                    id=f"{key}.1",
                    citation=f"AI analysis {today}: "
                    + "; ".join(f"{p.block} {p.level} ({p.why})" for p in parts),
                    source_type="expert_judgement",
                    published=None,
                    era=BaselineEra.UNKNOWN,
                    era_basis=ref.EraBasis.NOT_ESTABLISHED,
                    quality="low",
                )
            ],
        }
    )


# --- searching and saving ------------------------------------------------------------------


def search_web(cfg: QuickConfig, name: str) -> Researched:
    """Ask the AI for sources (only the feature's name is sent) and check every page."""
    research = cfg.research
    assert research is not None
    prompt = load_prompt(f"{research.prompt}.md")
    sections = ", ".join(f"{k} ({v})" for k, v in catalog_sections().items())
    system = prompt.replace("{{max_sources}}", str(research.max_sources)).replace(
        "{{sections}}", sections
    )
    try:
        result = get_llm_client().search_web(
            system=system,
            user=f"Feature: {name[:200]}",
            schema=ResearchReply,
            max_searches=research.max_searches,
        )
    except (LLMNotConfiguredError, LLMRefusedError) as exc:
        return Researched(reply=None, error=str(exc))
    checked = check_sources(result.output.sources, research, cfg.hours_per_person_day)
    return Researched(
        reply=result.output,
        checked=checked,
        model=result.model,
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
    )


def search(cfg: QuickConfig, name: str, catalog: ref.Catalog, standard: set[str]) -> Researched:
    """Web sources first (when enabled), then the AI analysis if too few checked out."""
    research = cfg.research
    assert research is not None
    found = search_web(cfg, name) if research.web_search else Researched(reply=None)
    if sum(s.ok for s in found.checked) >= research.min_verified_sources:
        return found
    analysis, model, tokens_in, tokens_out, error = analyse(cfg, name, catalog, standard)
    return found.model_copy(
        update={
            "analysis": analysis,
            "model": found.model or model,
            "input_tokens": found.input_tokens + tokens_in,
            "output_tokens": found.output_tokens + tokens_out,
            "error": found.error if analysis else (error or found.error),
        }
    )


def save(
    db: Session, user: User, cfg: QuickConfig, name: str, base_type: str, found: Researched
) -> ResearchedComponent:
    """Store the outcome: an active block (from web sources, else from the AI analysis), or a
    record that nothing usable was found (so the search is not repeated too soon)."""
    research = cfg.research
    assert research is not None
    key = slug(name)
    catalog = catalog_for(db, user.org_id)
    base = catalog.get(cfg.custom_feature_types[base_type].component)
    kept = [s for s in found.checked if s.ok]
    parts = (
        valid_parts(found.analysis.parts, catalog, standard_blocks(cfg)) if found.analysis else []
    )
    level_size: dict[str, Size] = {k: v.component_size for k, v in cfg.sizing.levels.items()}
    spec: ref.CatalogComponent | None = None
    method = "none"
    if found.reply is not None and len(kept) >= research.min_verified_sources:
        spec = build_component(
            key, name, found.reply, kept, base, research, cfg.hours_per_person_day
        )
        method = "web"
    elif found.analysis is not None and parts:
        spec = build_composed(key, name, found.analysis, parts, catalog, base, level_size)
        method = "analysis"
    old = db.scalars(
        scoped(ResearchedComponent, user.org_id).where(ResearchedComponent.key == key)
    ).first()
    if old is not None:  # only a no_evidence record is ever replaced
        db.delete(old)
        db.flush()
    row = ResearchedComponent(
        org_id=user.org_id,
        key=key,
        name=name[:200],
        section=(spec.section if spec else base.section) or "custom",
        base_type=base_type,
        status="active" if spec else "no_evidence",
        spec=spec.model_dump(mode="json") if spec else None,
        sources=[s.model_dump(mode="json") for s in found.checked]
        + [{"kind": "part", **p.model_dump(mode="json")} for p in parts],
        note=f"{method}: {len(kept)} of {len(found.checked)} web sources checked out"
        + (f"; {found.error}" if found.error else ""),
        model=found.model,
        prompt_version=research.analyse_prompt if method == "analysis" else research.prompt,
        input_tokens=found.input_tokens,
        output_tokens=found.output_tokens,
        created_by=user.id,
    )
    db.add(row)
    db.flush()
    if research.share:
        library.share(db, row, method)
    return row


def _recent_no_evidence(row: ResearchedComponent, days: int) -> bool:
    created = row.created_at if row.created_at.tzinfo else row.created_at.replace(tzinfo=UTC)
    return row.status == "no_evidence" and datetime.now(UTC) - created < timedelta(days=days)


def ai_available() -> bool:
    try:
        get_llm_client()
    except LLMNotConfiguredError:
        return False
    return True


def resolve_features(
    db: Session, user: User, cfg: QuickConfig, features: list[tuple[str, str]]
) -> list[str | None]:
    """For each (name, type): the catalog key that prices it, or None for the custom type.
    Catalog first; then (with an AI key) research, up to max_per_estimate features."""
    research = cfg.research
    catalog = catalog_for(db, user.org_id)
    threshold = research.match_threshold if research else Decimal(1)
    keys: list[str | None] = []
    wanted: list[int] = []
    for i, (name, _) in enumerate(features):
        block = find_block(name, catalog.components, threshold)
        keys.append(block.key if block else None)
        if block is None:
            wanted.append(i)
    if research is None or not wanted or research.max_per_estimate == 0 or not ai_available():
        return keys  # without an AI key the custom types price them, as before
    todo = []
    for i in wanted:
        old = db.scalars(
            scoped(ResearchedComponent, user.org_id).where(
                ResearchedComponent.key == slug(features[i][0])
            )
        ).first()
        if old is None or (
            old.status == "no_evidence"
            and not _recent_no_evidence(old, research.retry_no_evidence_days)
        ):  # a retired block stays retired: the generic block prices the feature
            todo.append(i)
    todo = todo[: research.max_per_estimate]
    standard = standard_blocks(cfg)
    with ThreadPoolExecutor(max_workers=research.concurrency) as pool:
        found = list(pool.map(lambda i: search(cfg, features[i][0], catalog, standard), todo))
    for i, outcome in zip(todo, found, strict=True):
        name, base_type = features[i]
        row = save(db, user, cfg, name, base_type, outcome)
        log.info(
            "research %s: %s (%s in / %s out tokens)",
            row.key,
            row.status,
            row.input_tokens,
            row.output_tokens,
        )
        if row.status == "active":
            keys[i] = row.key
    return keys


def research_rows(db: Session, org_id: str) -> list[ResearchedComponent]:
    return list(
        db.scalars(
            select(ResearchedComponent)
            .where(ResearchedComponent.org_id == org_id)
            .order_by(ResearchedComponent.created_at.desc())
        ).all()
    )

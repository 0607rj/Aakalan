"""The shared library of researched features (OPEN_QUESTIONS 142). Every block researched for
one organisation is also shared with all of them, so a feature researched once is priced for
everyone without another search, and the catalog grows with each new feature.

Only what is not confidential is shared: the feature's name, its section, the hours and the
public pages (or catalog blocks) they come from; never the organisation, project or document.
The table `shared_researched_components` is the live copy every request reads; the file
(settings.resolved_research_library, `seeds/research/library.yaml`) mirrors it, so the library
is kept in the repository and seeded into new installs. Estimates snapshot the blocks they use,
so a later addition never changes an estimate. `research.share` in quick_estimate.yaml turns
sharing off: then nothing new is shared and no organisation reads the shared blocks, so each
one is priced by its own research only (OPEN_QUESTIONS 185).

A newly shared block waits for the site owner (`pending`): only an approved (`active`) block
prices other companies' features, and only then is it written to the file. With
`research.auto_share` it is approved as it is shared (OPEN_QUESTIONS 214). Another company
sees it under an anonymous key (`shared_key`), never the words it was researched under
(OPEN_QUESTIONS 190)."""

import hashlib
import logging
import threading
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import ResearchedComponent, SharedResearchedComponent

log = logging.getLogger(__name__)

HEADER = """\
# Shared library of researched features (OPEN_QUESTIONS 142), written by the app.
# A feature the catalog lacked, researched once (checked web sources, else the AI's analysis
# as catalog blocks) and shared with every organisation; `make seed` loads it into new installs.
# Only the feature name, section, hours and public sources: never a company, project or tender.
# Removing an entry stops new installs loading it; an installed app keeps its copy until
# the row is retired. Estimates that used a block keep their own snapshot either way.
"""
_LOCK = threading.Lock()
SHARED_PREFIX = "researched_shared_"  # the anonymous keys other companies see


def public_sources(sources: list[Any]) -> list[Any]:
    """The sources another company may see: the public pages as they are, and for an AI analysis
    only which catalog blocks at which level (the AI's `why` is written from one company's own
    words, so it stays with that company; OPEN_QUESTIONS 202)."""
    out: list[Any] = []
    for s in sources:
        if isinstance(s, dict) and s.get("kind") == "part":
            out.append({k: v for k, v in s.items() if k != "why"})
        else:
            out.append(s)
    return out


def public_spec(spec: dict[str, Any], sources: list[Any]) -> dict[str, Any]:
    """The catalog block another company may see: the same name, section, hours and sources,
    with no description and, for an AI analysis, a citation that names only the catalog blocks
    (both are the AI's words about one company's feature). Hours and task shares are unchanged,
    so a cleaned block prices exactly as before."""
    parts = [s for s in sources if isinstance(s, dict) and s.get("kind") == "part"]
    evidence = []
    for e in spec.get("evidence") or []:
        citation = str(e.get("citation", ""))
        if parts and citation.startswith("AI analysis"):
            head = citation.split(":", 1)[0]
            blocks = "; ".join(f"{p.get('block')} {p.get('level')}" for p in parts)
            e = {**e, "citation": f"{head}: {blocks}"}
        evidence.append(e)
    return {**spec, "description": "", "evidence": evidence}


def shared_key(key: str) -> str:
    """The key another company prices a shared block under: a hash, so it carries none of the
    words of the name it was researched under."""
    return SHARED_PREFIX + hashlib.sha256(key.encode()).hexdigest()[:16]


class LibraryEntry(BaseModel):
    key: str
    name: str
    section: str
    base_type: str
    method: str  # web / analysis
    added: date
    spec: dict[str, Any]  # catalog component
    sources: list[Any]


def read_library(path: Path) -> list[LibraryEntry]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    return [LibraryEntry.model_validate(b) for b in data.get("blocks") or []]


def _write(path: Path, entries: list[LibraryEntry]) -> None:
    """Whole file to a temporary name, then renamed: a reader never sees half a file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    body = yaml.safe_dump(
        {"blocks": [e.model_dump(mode="json") for e in entries]},
        sort_keys=False,
        allow_unicode=True,
        width=100,
    )
    tmp = path.with_suffix(".tmp")
    tmp.write_text(HEADER + body, encoding="utf-8")
    tmp.replace(path)


def merge_library(path: Path, other: Path) -> int:
    """Add `other`'s entries that `path` lacks (by key), keeping `path`'s order: the server's
    own additions put back after an update pulls the repository's file (deploy/update.sh)."""
    with _LOCK:
        entries = read_library(path)
        keys = {e.key for e in entries}
        extra = [e for e in read_library(other) if e.key not in keys]
        if extra:
            _write(path, [*entries, *extra])
    return len(extra)


def _append(entry: LibraryEntry) -> None:
    path = get_settings().resolved_research_library
    try:
        with _LOCK:
            entries = read_library(path)
            if all(e.key != entry.key for e in entries):
                _write(path, [*entries, entry])
    except OSError as exc:  # a read-only install still shares through the table
        log.warning("research library %s not written: %s", path, exc)


def _remove(key: str) -> None:
    path = get_settings().resolved_research_library
    try:
        with _LOCK:
            entries = read_library(path)
            kept = [e for e in entries if e.key != key]
            if len(kept) != len(entries):
                _write(path, kept)
    except OSError as exc:
        log.warning("research library %s not written: %s", path, exc)


def approve(row: SharedResearchedComponent) -> None:
    """The owner lets a shared block price other companies' features; the file gets it too."""
    row.status = "active"
    _append(
        LibraryEntry(
            key=row.key,
            name=row.name,
            section=row.section,
            base_type=row.base_type,
            method=row.method,
            added=datetime.now(UTC).date(),
            spec=public_spec(row.spec, public_sources(row.sources)),
            sources=public_sources(row.sources),
        )
    )


def retire(row: SharedResearchedComponent) -> None:
    """No longer offered to anyone (estimates that used it keep their snapshot); off the file."""
    row.status = "retired"
    _remove(row.key)


def share(db: Session, row: ResearchedComponent, method: str) -> None:
    """Offer an active researched block to every company (once per key). It waits for the
    owner's approval (`approve`) before it prices anyone else's features or reaches the file:
    its name is one company's own text."""
    if row.status != "active" or row.spec is None:
        return
    if db.scalars(
        select(SharedResearchedComponent).where(SharedResearchedComponent.key == row.key)
    ).first():
        return
    sources = public_sources([s for s in row.sources if s.get("kind") == "part" or s.get("ok")])
    shared = SharedResearchedComponent(
        key=row.key,
        name=row.name,
        section=row.section,
        base_type=row.base_type,
        method=method,
        spec=public_spec(row.spec, sources),
        sources=sources,
        status="pending",
    )
    db.add(shared)
    if auto_share_on():
        approve(shared)
    db.flush()


def sharing_on() -> bool:
    """`research.share` in quick_estimate.yaml (off when there is no research block)."""
    from app.services.quick.config import quick_config

    research = quick_config().research
    return bool(research and research.share)


def auto_share_on() -> bool:
    """`research.auto_share` in quick_estimate.yaml: shared blocks need no owner approval."""
    from app.services.quick.config import quick_config

    research = quick_config().research
    return bool(research and research.auto_share)


def shared_blocks(db: Session) -> list[SharedResearchedComponent]:
    """The approved shared blocks, or none while sharing is off."""
    if not sharing_on():
        return []
    return list(
        db.scalars(
            select(SharedResearchedComponent)
            .where(SharedResearchedComponent.status == "active")
            .order_by(SharedResearchedComponent.created_at, SharedResearchedComponent.key)
        ).all()
    )


def seed_library(db: Session, path: Path) -> int:
    """Load the file's entries the table lacks (a new install, or entries from the repo)."""
    known = set(db.scalars(select(SharedResearchedComponent.key)).all())
    added = 0
    for e in read_library(path):
        if e.key in known:
            continue
        db.add(
            SharedResearchedComponent(
                key=e.key,
                name=e.name,
                section=e.section,
                base_type=e.base_type,
                method=e.method,
                spec=public_spec(e.spec, public_sources(e.sources)),
                sources=public_sources(e.sources),
            )
        )
        known.add(e.key)
        added += 1
    db.flush()
    return added


def share_existing(db: Session) -> int:
    """Share the active blocks researched before sharing existed (each key once)."""
    known = set(db.scalars(select(SharedResearchedComponent.key)).all())
    rows = db.scalars(
        select(ResearchedComponent)
        .where(ResearchedComponent.status == "active")
        .order_by(ResearchedComponent.created_at)
    ).all()
    shared = 0
    for row in rows:
        if row.key not in known:
            share(db, row, row.note.split(":", 1)[0] or "web")
            known.add(row.key)
            shared += 1
    return shared

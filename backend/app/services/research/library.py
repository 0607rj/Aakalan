"""The shared library of researched features (OPEN_QUESTIONS 142). Every block researched for
one organisation is also shared with all of them, so a feature researched once is priced for
everyone without another search, and the catalog grows with each new feature.

Only what is not confidential is shared: the feature's name, its section, the hours and the
public pages (or catalog blocks) they come from; never the organisation, project or document.
The table `shared_researched_components` is the live copy every request reads; the file
(settings.resolved_research_library, `seeds/research/library.yaml`) mirrors it, so the library
is kept in the repository and seeded into new installs. Estimates snapshot the blocks they use,
so a later addition never changes an estimate. `research.share` in quick_estimate.yaml turns
sharing off."""

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


def _append(entry: LibraryEntry) -> None:
    path = get_settings().resolved_research_library
    try:
        with _LOCK:
            entries = read_library(path)
            if all(e.key != entry.key for e in entries):
                _write(path, [*entries, entry])
    except OSError as exc:  # a read-only install still shares through the table
        log.warning("research library %s not written: %s", path, exc)


def share(db: Session, row: ResearchedComponent, method: str) -> None:
    """Share an active researched block (once per key): the table now, the file alongside."""
    if row.status != "active" or row.spec is None:
        return
    if db.scalars(
        select(SharedResearchedComponent).where(SharedResearchedComponent.key == row.key)
    ).first():
        return
    sources = [s for s in row.sources if s.get("kind") == "part" or s.get("ok")]
    db.add(
        SharedResearchedComponent(
            key=row.key,
            name=row.name,
            section=row.section,
            base_type=row.base_type,
            method=method,
            spec=row.spec,
            sources=sources,
        )
    )
    db.flush()
    _append(
        LibraryEntry(
            key=row.key,
            name=row.name,
            section=row.section,
            base_type=row.base_type,
            method=method,
            added=datetime.now(UTC).date(),
            spec=row.spec,
            sources=sources,
        )
    )


def shared_blocks(db: Session) -> list[SharedResearchedComponent]:
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
                spec=e.spec,
                sources=e.sources,
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

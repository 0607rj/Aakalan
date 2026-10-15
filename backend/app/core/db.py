"""Database engine, session factory and per-connection SQLite configuration.

All database access goes through SQLAlchemy so SQLite can be swapped for PostgreSQL by
changing `DATABASE_URL` (architecture rule 9).
"""

import logging
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings, get_settings

log = logging.getLogger(__name__)

SQLITE_PRAGMAS = (
    "PRAGMA journal_mode = WAL",
    "PRAGMA busy_timeout = 5000",
    "PRAGMA foreign_keys = ON",
    "PRAGMA synchronous = NORMAL",
)


def _configure_sqlite_connection(dbapi_conn: Any, load_vec: bool) -> None:
    if load_vec:
        import sqlite_vec

        dbapi_conn.enable_load_extension(True)
        sqlite_vec.load(dbapi_conn)
        dbapi_conn.enable_load_extension(False)
    cursor = dbapi_conn.cursor()
    for pragma in SQLITE_PRAGMAS:
        cursor.execute(pragma)
    cursor.close()


def make_engine(url: str, *, sqlite_vec_enabled: bool) -> Engine:
    is_sqlite = url.startswith("sqlite")
    connect_args: dict[str, Any] = {"check_same_thread": False} if is_sqlite else {}
    if is_sqlite and ":memory:" not in url:
        db_path = Path(url.split("///", 1)[1])
        db_path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(url, connect_args=connect_args)
    if is_sqlite:

        @event.listens_for(engine, "connect")
        def _on_connect(dbapi_conn: Any, _record: Any) -> None:
            _configure_sqlite_connection(dbapi_conn, sqlite_vec_enabled)

    return engine


_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None


def init_engine(settings: Settings | None = None) -> Engine:
    global _engine, _session_factory
    settings = settings or get_settings()
    _engine = make_engine(
        settings.resolved_database_url, sqlite_vec_enabled=settings.sqlite_vec_enabled
    )
    _session_factory = sessionmaker(bind=_engine, expire_on_commit=False)
    return _engine


def get_engine() -> Engine:
    return _engine if _engine is not None else init_engine()


def get_session_factory() -> sessionmaker[Session]:
    if _session_factory is None:
        init_engine()
    assert _session_factory is not None
    return _session_factory


def get_db() -> Iterator[Session]:
    """FastAPI dependency yielding a session that is closed after the request."""
    session = get_session_factory()()
    try:
        yield session
    finally:
        session.close()

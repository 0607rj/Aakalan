from sqlalchemy import text
from sqlalchemy.orm import Session


def test_sqlite_pragmas_applied(db: Session) -> None:
    assert db.execute(text("PRAGMA journal_mode")).scalar() == "wal"
    assert db.execute(text("PRAGMA foreign_keys")).scalar() == 1
    assert db.execute(text("PRAGMA busy_timeout")).scalar() == 5000
    assert db.execute(text("PRAGMA synchronous")).scalar() == 1  # NORMAL


def test_sqlite_vec_loaded(db: Session) -> None:
    assert str(db.execute(text("SELECT vec_version()")).scalar()).startswith("v")

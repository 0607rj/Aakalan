"""Alembic environment. The database URL comes from app settings, not alembic.ini.

`render_as_batch=True` lets ALTER TABLE work on SQLite (brief Section 4).
"""

from logging.config import fileConfig

from alembic import context

from app.core.config import get_settings
from app.core.db import make_engine
from app.models import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name, disable_existing_loggers=False)

target_metadata = Base.metadata


def _url() -> str:
    return config.attributes.get("database_url") or get_settings().resolved_database_url


def run_migrations_offline() -> None:
    context.configure(
        url=_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    settings = get_settings()
    engine = make_engine(_url(), sqlite_vec_enabled=settings.sqlite_vec_enabled)
    with engine.connect() as connection:
        sqlite = connection.dialect.name == "sqlite"
        if sqlite:
            # Batch mode drops and re-creates a table; with foreign keys on, that drop
            # cascade-deletes every row pointing at it (2026-11-02 it emptied users and
            # estimates). Off for the migration (a no-op inside a transaction, so set first),
            # then checked after.
            connection.exec_driver_sql("PRAGMA foreign_keys=OFF")
            connection.commit()
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()
        if sqlite:
            broken = connection.exec_driver_sql("PRAGMA foreign_key_check").fetchall()
            connection.commit()
            if broken:
                raise RuntimeError(f"Migration left broken foreign keys: {broken[:5]}")
    engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

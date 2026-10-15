"""Huey background-job instance (SQLite storage at `data/huey.db`).

Run a worker with: `uv run huey_consumer app.jobs.huey`.
"""

from huey import SqliteHuey

from app.core.config import get_settings

_settings = get_settings()
_settings.data_dir.mkdir(parents=True, exist_ok=True)

huey = SqliteHuey(
    "aakalan",
    filename=str(_settings.data_dir / "huey.db"),
    immediate=_settings.environment == "test",
)


@huey.task()  # type: ignore[untyped-decorator]
def ping() -> str:
    """Smoke-test task proving the worker is wired up."""
    return "pong"

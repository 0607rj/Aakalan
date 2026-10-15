"""Test fixtures: every test session gets an isolated temporary SQLite database,
migrated with Alembic (so the migrations are exercised too)."""

import os
import tempfile
from collections.abc import Iterator
from pathlib import Path

import pytest

_TMP_DATA = Path(tempfile.mkdtemp(prefix="aakalan-test-"))
os.environ["ENVIRONMENT"] = "test"
os.environ["DATA_DIR"] = str(_TMP_DATA)
os.environ["DATABASE_URL"] = f"sqlite:///{(_TMP_DATA / 'test.db').as_posix()}"

from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.core import db as db_module  # noqa: E402
from app.core.config import BACKEND_DIR, get_settings  # noqa: E402

TEST_PASSWORD = "test-password-123"


@pytest.fixture(scope="session")
def database_url() -> Iterator[str]:
    get_settings.cache_clear()
    url = get_settings().resolved_database_url
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.attributes["database_url"] = url
    command.upgrade(cfg, "head")
    db_module.init_engine()
    yield url
    db_module.get_engine().dispose()


@pytest.fixture(scope="session")
def seeded(database_url: str) -> None:
    from app.services.seeding.database import seed_reference
    from app.services.seeding.reference import load_reference
    from app.services.seeding.users import seed_demo_users

    with db_module.get_session_factory()() as session:
        assert seed_reference(session, load_reference(get_settings().seeds_dir)) == []
        seed_demo_users(session, TEST_PASSWORD)
        session.commit()


@pytest.fixture
def db(seeded: None) -> Iterator[Session]:
    with db_module.get_session_factory()() as session:
        yield session


@pytest.fixture(scope="session")
def client(seeded: None) -> TestClient:
    from app.main import create_app

    return TestClient(create_app())


def login(client: TestClient, email: str, password: str = TEST_PASSWORD) -> dict[str, str]:
    response = client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture(scope="session")
def admin_headers(client: TestClient) -> dict[str, str]:
    return login(client, "admin@aakalan.local")


@pytest.fixture(scope="session")
def estimator_headers(client: TestClient) -> dict[str, str]:
    return login(client, "estimator@aakalan.local")


@pytest.fixture(scope="session")
def finance_headers(client: TestClient) -> dict[str, str]:
    return login(client, "finance@aakalan.local")


@pytest.fixture(scope="session")
def viewer_headers(client: TestClient) -> dict[str, str]:
    return login(client, "viewer@aakalan.local")

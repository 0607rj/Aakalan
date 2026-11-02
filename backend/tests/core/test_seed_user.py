"""The first account (OPEN_QUESTIONS 200): its email is a setting (never a public mailbox in the
code), production refuses the example password, and a changed email adds no second account."""

from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.models import User
from app.models.base import Base
from app.services.seeding.users import WeakSeedPasswordError, seed_demo_users

STRONG = "a-long-and-strong-password"


@pytest.fixture
def session() -> Iterator[Session]:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


@pytest.fixture
def env(monkeypatch: pytest.MonkeyPatch) -> Iterator[pytest.MonkeyPatch]:
    yield monkeypatch
    get_settings.cache_clear()


def emails(session: Session) -> list[str]:
    return list(session.scalars(select(User.email)))


def test_the_default_email_is_one_nobody_receives() -> None:
    assert Settings.model_fields["seed_user_email"].default == "admin@example.com"


def test_the_email_comes_from_the_settings(session: Session, env: pytest.MonkeyPatch) -> None:
    env.setenv("SEED_USER_EMAIL", "owner@mycompany.in")
    get_settings.cache_clear()
    seed_demo_users(session, STRONG)
    assert emails(session) == ["owner@mycompany.in"]


def test_a_changed_email_adds_no_second_account(session: Session, env: pytest.MonkeyPatch) -> None:
    env.setenv("SEED_USER_EMAIL", "first@mycompany.in")
    get_settings.cache_clear()
    seed_demo_users(session, STRONG)
    env.setenv("SEED_USER_EMAIL", "owner@mycompany.in")
    get_settings.cache_clear()
    seed_demo_users(session, STRONG)
    assert emails(session) == ["first@mycompany.in"]


def test_production_refuses_the_example_password(session: Session, env: pytest.MonkeyPatch) -> None:
    env.setenv("ENVIRONMENT", "production")
    get_settings.cache_clear()
    with pytest.raises(WeakSeedPasswordError):
        seed_demo_users(session, "admin123")


def test_a_demo_server_may_allow_it_for_the_first_account_only(
    session: Session, env: pytest.MonkeyPatch
) -> None:
    env.setenv("ENVIRONMENT", "production")
    env.setenv("SEED_ALLOW_WEAK_PASSWORD", "true")
    env.setenv("SEED_USER_EMAIL", "owner@mycompany.in")
    get_settings.cache_clear()
    seed_demo_users(session, "admin123")
    assert emails(session) == ["owner@mycompany.in"]

"""Demo organisation and users for local development (never run in production)."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.security import hash_password
from app.models import Organisation, Role, User
from app.models.base import utcnow

DEMO_ORG_NAME = "Demo Systems Integrator"
DEMO_EMAIL = "admin@gmail.com"
# Roles are switched off for now: the single demo user has full access (admin).
DEMO_USERS: tuple[tuple[str, str, Role], ...] = ((DEMO_EMAIL, "Demo User", Role.ADMIN),)


class WeakSeedPasswordError(RuntimeError):
    """The first account would be created with the example password on a production server."""


def weak_seed_password(password: str) -> bool:
    """The example password (the settings default) or one shorter than sign-up allows."""
    default = Settings.model_fields["seed_user_password"].default
    return password == default or len(password) < get_settings().password_min_length


def seed_demo_users(
    session: Session, password: str, users: tuple[tuple[str, str, Role], ...] = DEMO_USERS
) -> Organisation:
    """Create the demo organisation and its users. Idempotent: an account that exists keeps its
    password. In production an account is never created with a weak SEED_USER_PASSWORD (the
    first account signs in to the server; with the example password anyone could)."""
    production = get_settings().environment == "production"
    org = session.scalars(select(Organisation).where(Organisation.name == DEMO_ORG_NAME)).first()
    if org is None:
        org = Organisation(name=DEMO_ORG_NAME)
        session.add(org)
        session.flush()
    for email, full_name, role in users:
        if session.scalars(select(User).where(User.email == email)).first() is None:
            if production and weak_seed_password(password):
                raise WeakSeedPasswordError(
                    f"Set a strong SEED_USER_PASSWORD in .env before {email} is created."
                )
            session.add(
                User(
                    org_id=org.id,
                    email=email,
                    full_name=full_name,
                    role=role,
                    password_hash=hash_password(password),
                    email_verified_at=utcnow(),
                )
            )
    session.flush()
    return org

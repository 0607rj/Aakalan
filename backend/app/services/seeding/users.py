"""Demo organisation and users for local development (never run in production)."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models import Organisation, Role, User
from app.models.base import utcnow

DEMO_ORG_NAME = "Demo Systems Integrator"
DEMO_EMAIL = "admin@gmail.com"
# Roles are switched off for now: the single demo user has full access (admin).
DEMO_USERS: tuple[tuple[str, str, Role], ...] = ((DEMO_EMAIL, "Demo User", Role.ADMIN),)


def seed_demo_users(
    session: Session, password: str, users: tuple[tuple[str, str, Role], ...] = DEMO_USERS
) -> Organisation:
    """Create the demo organisation and its users. Idempotent."""
    org = session.scalars(select(Organisation).where(Organisation.name == DEMO_ORG_NAME)).first()
    if org is None:
        org = Organisation(name=DEMO_ORG_NAME)
        session.add(org)
        session.flush()
    for email, full_name, role in users:
        if session.scalars(select(User).where(User.email == email)).first() is None:
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

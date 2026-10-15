"""Demo organisation and users for local development (never run in production)."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models import Organisation, Role, User

DEMO_ORG_NAME = "Demo Systems Integrator"
DEMO_USERS = (
    ("admin@aakalan.local", "Demo Admin", Role.ADMIN),
    ("finance@aakalan.local", "Demo Finance", Role.FINANCE),
    ("estimator@aakalan.local", "Demo Estimator", Role.ESTIMATOR),
    ("viewer@aakalan.local", "Demo Viewer", Role.VIEWER),
)


def seed_demo_users(session: Session, password: str) -> Organisation:
    """Create the demo organisation and one user per role. Idempotent."""
    org = session.scalars(select(Organisation).where(Organisation.name == DEMO_ORG_NAME)).first()
    if org is None:
        org = Organisation(name=DEMO_ORG_NAME)
        session.add(org)
        session.flush()
    for email, full_name, role in DEMO_USERS:
        if session.scalars(select(User).where(User.email == email)).first() is None:
            session.add(
                User(
                    org_id=org.id,
                    email=email,
                    full_name=full_name,
                    role=role,
                    password_hash=hash_password(password),
                )
            )
    session.flush()
    return org

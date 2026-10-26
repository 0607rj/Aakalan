"""Common FastAPI dependencies: DB session, current user, role checks."""

from collections.abc import Callable
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.db import get_db
from app.core.security import decode_access_token
from app.models import Role, User

DbSession = Annotated[Session, Depends(get_db)]
_bearer = HTTPBearer(auto_error=False)


# Methods that only read: all the site owner may do while looking at someone else's account.
READ_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})


def get_current_user(
    request: Request,
    db: DbSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> User:
    unauthorized = HTTPException(
        status.HTTP_401_UNAUTHORIZED,
        "Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise unauthorized
    try:
        payload = decode_access_token(credentials.credentials)
    except jwt.PyJWTError as exc:
        raise unauthorized from exc
    user = db.get(User, payload.get("sub"))
    if (
        user is None
        or not user.is_active
        or user.org_id != payload.get("org")
        or payload.get("tv", 0) != user.token_version
    ):
        raise unauthorized
    acting = payload.get("act")
    if acting is not None:
        # The site owner looking at this account: only while still an active owner, read only.
        owner = db.get(User, acting)
        if owner is None or not owner.is_active or not is_owner(owner):
            raise unauthorized
        if request.method not in READ_METHODS:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                "Read only: you are viewing another account. Go back to Admin to make changes.",
            )
        request.state.acting_owner = owner
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]

FINANCE_ROLES = frozenset({Role.ADMIN, Role.FINANCE})
EDITOR_ROLES = frozenset({Role.ADMIN, Role.ESTIMATOR, Role.FINANCE})


def require_roles(*roles: Role) -> Callable[[User], User]:
    allowed = frozenset(roles)

    def checker(user: CurrentUser) -> User:
        if user.role not in allowed:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient role")
        return user

    return checker


EditorUser = Annotated[User, Depends(require_roles(*EDITOR_ROLES))]
AdminUser = Annotated[User, Depends(require_roles(Role.ADMIN))]
FinanceUser = Annotated[User, Depends(require_roles(*FINANCE_ROLES))]


def is_owner(user: User) -> bool:
    """The product owner: the sign-in email is in settings `owner_emails` (any case)."""
    return user.email.lower() in {e.lower() for e in get_settings().owner_emails}


def require_owner(user: CurrentUser) -> User:
    if not is_owner(user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not available")
    return user


OwnerUser = Annotated[User, Depends(require_owner)]


def can_see_margin(user: User) -> bool:
    return user.role in FINANCE_ROLES

"""Common FastAPI dependencies: DB session, current user, role checks."""

from collections.abc import Callable
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.security import decode_access_token
from app.models import Role, User

DbSession = Annotated[Session, Depends(get_db)]
_bearer = HTTPBearer(auto_error=False)


def get_current_user(
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
    if user is None or not user.is_active or user.org_id != payload.get("org"):
        raise unauthorized
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


def can_see_margin(user: User) -> bool:
    return user.role in FINANCE_ROLES

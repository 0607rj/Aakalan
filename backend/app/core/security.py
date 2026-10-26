"""Password hashing (argon2) and JWT access tokens."""

from datetime import timedelta
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from app.core.config import get_settings
from app.models.base import utcnow

_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return False


def create_access_token(
    user_id: str,
    org_id: str,
    role: str,
    token_version: int = 0,
    acting_owner: str | None = None,
) -> str:
    """`tv`: the user's token version; a password reset or change raises it, so every token
    issued before stops working (api/deps.py). `act`: the site owner's user id when the owner
    opens this account to look at it (read only, api/owner.py)."""
    settings = get_settings()
    now = utcnow()
    payload: dict[str, Any] = {
        "sub": user_id,
        "org": org_id,
        "role": role,
        "tv": token_version,
        **({"act": acting_owner} if acting_owner else {}),
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    """Raises `jwt.PyJWTError` if the token is invalid or expired."""
    settings = get_settings()
    payload: dict[str, Any] = jwt.decode(
        token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
    )
    return payload

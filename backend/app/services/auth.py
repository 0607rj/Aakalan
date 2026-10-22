"""Sign-up, email verification and password reset with emailed one-time codes.

A code is 6 random digits, stored only as an HMAC (keyed with the JWT secret) of purpose, user
and code. It works once, for `otp_minutes`, for `otp_max_attempts` tries; a new code replaces
the old one, at most one per `otp_resend_seconds` and `otp_max_per_hour` an hour. A password
reset or change raises the user's token version, which signs out every older token."""

import hashlib
import hmac
import re
import secrets
from datetime import UTC, datetime, timedelta
from typing import Literal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import hash_password
from app.models import OneTimeCode, Organisation, Role, User
from app.models.base import utcnow
from app.services.email import get_email_sender

Purpose = Literal["verify_email", "reset_password"]
EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

SUBJECTS: dict[Purpose, str] = {
    "verify_email": "Your Aakalan verification code",
    "reset_password": "Your Aakalan password reset code",
}
ACTIONS: dict[Purpose, str] = {
    "verify_email": "confirm your email address",
    "reset_password": "reset your password",
}


class AuthError(Exception):
    """A refusal with a message safe to show."""

    def __init__(self, message: str, status: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status = status


class TooSoonError(AuthError):
    def __init__(self, seconds: int) -> None:
        super().__init__(f"Please wait {seconds} seconds before asking for another code.", 429)


WRONG_CODE = "That code is wrong or has expired. Ask for a new one."


def normalise_email(email: str) -> str:
    return email.strip().lower()


def find_user(db: Session, email: str) -> User | None:
    return db.scalars(select(User).where(func.lower(User.email) == normalise_email(email))).first()


def check_password(password: str) -> None:
    n = get_settings().password_min_length
    if len(password) < n:
        raise AuthError(f"Use a password of at least {n} characters.", 422)
    if len(password) > 128:
        raise AuthError("Use a password of at most 128 characters.", 422)


def _aware(t: datetime) -> datetime:
    return t if t.tzinfo else t.replace(tzinfo=UTC)


def _hash(purpose: Purpose, user_id: str, code: str) -> str:
    key = get_settings().jwt_secret.encode()
    return hmac.new(key, f"{purpose}:{user_id}:{code}".encode(), hashlib.sha256).hexdigest()


def _codes(db: Session, user: User, purpose: Purpose) -> list[OneTimeCode]:
    return list(
        db.scalars(
            select(OneTimeCode)
            .where(OneTimeCode.user_id == user.id, OneTimeCode.purpose == purpose)
            .order_by(OneTimeCode.created_at.desc())
        ).all()
    )


def send_code(db: Session, user: User, purpose: Purpose) -> None:
    """Email a new code (the older ones stop working). Raises TooSoonError within the
    resend wait or past the hourly limit."""
    s = get_settings()
    now = utcnow()
    codes = _codes(db, user, purpose)
    if codes:
        waited = (now - _aware(codes[0].created_at)).total_seconds()
        if waited < s.otp_resend_seconds:
            raise TooSoonError(int(s.otp_resend_seconds - waited) + 1)
    hour = [c for c in codes if now - _aware(c.created_at) < timedelta(hours=1)]
    if len(hour) >= s.otp_max_per_hour:
        oldest = min(_aware(c.created_at) for c in hour)
        raise TooSoonError(int((oldest + timedelta(hours=1) - now).total_seconds()) + 1)
    for c in codes:
        if c.used_at is None:
            c.used_at = now
    code = f"{secrets.randbelow(10**6):06d}"
    db.add(
        OneTimeCode(
            user_id=user.id,
            purpose=purpose,
            code_hash=_hash(purpose, user.id, code),
            expires_at=now + timedelta(minutes=s.otp_minutes),
        )
    )
    db.flush()
    get_email_sender().send(
        user.email,
        SUBJECTS[purpose],
        f"Hello {user.full_name or 'there'},\n\n"
        f"Your code to {ACTIONS[purpose]} is {code}.\n"
        f"It works for {s.otp_minutes} minutes.\n\n"
        "If you did not ask for it, you can ignore this email.\n\nAakalan",
    )


def use_code(db: Session, user: User, purpose: Purpose, code: str) -> bool:
    """True if `code` is the user's current code for `purpose` (then it is used up). Every
    try counts; the caller commits even when this returns False."""
    now = utcnow()
    current = next(
        (c for c in _codes(db, user, purpose) if c.used_at is None),
        None,
    )
    if current is None or _aware(current.expires_at) < now:
        return False
    current.attempts += 1
    if current.attempts > get_settings().otp_max_attempts:
        current.used_at = now
        return False
    if not hmac.compare_digest(current.code_hash, _hash(purpose, user.id, code.strip())):
        return False
    current.used_at = now
    return True


def sign_up(db: Session, full_name: str, company: str, email: str, password: str) -> User:
    """A new company with this person as its admin, not yet verified; a code is emailed.
    Signing up again before verifying updates the details and sends a new code."""
    if not get_settings().signup_enabled:
        raise AuthError("Sign-up is closed. Ask your company admin for an account.", 403)
    email = normalise_email(email)
    if not EMAIL.match(email):
        raise AuthError("Enter a valid email address.", 422)
    check_password(password)
    full_name, company = full_name.strip(), company.strip()
    if not full_name or not company:
        raise AuthError("Enter your name and your company's name.", 422)
    user = find_user(db, email)
    if user is not None and user.email_verified_at is not None:
        raise AuthError(
            "An account with this email already exists. Sign in, or reset your password.", 409
        )
    taken = db.scalars(
        select(Organisation).where(func.lower(Organisation.name) == company.lower())
    ).first()
    if taken is not None and (user is None or taken.id != user.org_id):
        raise AuthError(
            "A company with this name is already registered. Ask its admin to add you, or use "
            "a different name.",
            409,
        )
    if user is None:
        org = Organisation(name=company)
        db.add(org)
        db.flush()
        user = User(
            org_id=org.id,
            email=email,
            full_name=full_name,
            role=Role.ADMIN,
            password_hash=hash_password(password),
        )
        db.add(user)
        db.flush()
    else:  # not verified yet: whoever proves the address with the code owns these details
        user.full_name = full_name
        user.password_hash = hash_password(password)
        user.organisation.name = company
    send_code(db, user, "verify_email")
    return user


def verify_email(db: Session, email: str, code: str) -> User:
    user = find_user(db, email)
    if user is None or not user.is_active or not use_code(db, user, "verify_email", code):
        raise AuthError(WRONG_CODE)
    user.email_verified_at = user.email_verified_at or utcnow()
    return user


def reset_password(db: Session, email: str, code: str, new_password: str) -> User:
    check_password(new_password)
    user = find_user(db, email)
    if user is None or not user.is_active or not use_code(db, user, "reset_password", code):
        raise AuthError(WRONG_CODE)
    set_password(user, new_password)
    user.email_verified_at = user.email_verified_at or utcnow()  # the code proved the address
    return user


def set_password(user: User, password: str) -> None:
    """New password; every token issued before stops working."""
    user.password_hash = hash_password(password)
    user.token_version += 1

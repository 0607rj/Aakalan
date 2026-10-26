"""Sign-up, sign-in (JWT), email verification and password reset by emailed codes
(services/auth.py)."""

from fastapi import APIRouter, HTTPException, Request, status

from app.api.deps import CurrentUser, DbSession, is_owner
from app.core.security import create_access_token, verify_password
from app.models import User
from app.schemas.auth import (
    ChangePasswordRequest,
    CodeSent,
    EmailRequest,
    LoginRequest,
    ResetPasswordRequest,
    SignupRequest,
    TokenResponse,
    UserOut,
    VerifyEmailRequest,
)
from app.services import auth
from app.services.email import EmailNotConfiguredError

router = APIRouter(prefix="/auth", tags=["auth"])

NOT_VERIFIED = "Email not verified"


def user_out(user: User) -> UserOut:
    return UserOut(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        org_id=user.org_id,
        org_name=user.organisation.name,
        is_owner=is_owner(user),
    )


def token_for(user: User) -> TokenResponse:
    token = create_access_token(user.id, user.org_id, user.role.value, user.token_version)
    return TokenResponse(access_token=token, user=user_out(user))


def _refused(db: DbSession, exc: auth.AuthError) -> HTTPException:
    """Keep what the refusal recorded (a wrong code counts as a try), then refuse."""
    db.commit()
    return HTTPException(exc.status, exc.message)


def _no_email() -> HTTPException:
    return HTTPException(
        status.HTTP_503_SERVICE_UNAVAILABLE, "We could not send the email. Please try again later."
    )


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: DbSession) -> TokenResponse:
    user = auth.find_user(db, body.email)
    if user is None or not user.is_active or not verify_password(body.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")
    if user.email_verified_at is None:  # only after the password: says nothing to strangers
        raise HTTPException(status.HTTP_403_FORBIDDEN, NOT_VERIFIED)
    return token_for(user)


@router.post("/signup", response_model=CodeSent, status_code=status.HTTP_201_CREATED)
def signup(body: SignupRequest, db: DbSession) -> CodeSent:
    """Your own account (and private space); sign in after confirming the emailed code."""
    try:
        user = auth.sign_up(db, body.full_name, body.email, body.password, body.company)
    except auth.AuthError as exc:
        db.rollback()
        raise HTTPException(exc.status, exc.message) from exc
    except EmailNotConfiguredError as exc:
        db.rollback()
        raise _no_email() from exc
    db.commit()
    return CodeSent(email=user.email, message=f"We sent a 6-digit code to {user.email}.")


@router.post("/verify-email", response_model=TokenResponse)
def verify_email(body: VerifyEmailRequest, db: DbSession) -> TokenResponse:
    """Confirm the address with the emailed code; signs you in."""
    try:
        user = auth.verify_email(db, body.email, body.code)
    except auth.AuthError as exc:
        raise _refused(db, exc) from exc
    db.commit()
    return token_for(user)


@router.post("/verify-email/resend", response_model=CodeSent)
def resend_verification(body: EmailRequest, db: DbSession) -> CodeSent:
    """A new code for an account not yet verified (the same answer for any other address)."""
    user = auth.find_user(db, body.email)
    email = auth.normalise_email(body.email)
    if user is not None and user.is_active and user.email_verified_at is None:
        try:
            auth.send_code(db, user, "verify_email")
        except auth.AuthError as exc:
            raise _refused(db, exc) from exc
        except EmailNotConfiguredError as exc:
            raise _no_email() from exc
        db.commit()
    return CodeSent(email=email, message=f"If {email} is waiting for a code, we sent a new one.")


@router.post("/password/forgot", response_model=CodeSent)
def forgot_password(body: EmailRequest, db: DbSession) -> CodeSent:
    """Email a reset code. The answer is the same whether or not the account exists."""
    email = auth.normalise_email(body.email)
    user = auth.find_user(db, email)
    if user is not None and user.is_active:
        try:
            auth.send_code(db, user, "reset_password")
            db.commit()
        except auth.TooSoonError:
            db.rollback()  # a code went out a moment ago: say nothing different
        except EmailNotConfiguredError as exc:
            raise _no_email() from exc
    return CodeSent(email=email, message=f"If an account uses {email}, we sent it a 6-digit code.")


@router.post("/password/reset", response_model=TokenResponse)
def reset_password(body: ResetPasswordRequest, db: DbSession) -> TokenResponse:
    """New password with the emailed code; signs you in and signs out every other session."""
    try:
        user = auth.reset_password(db, body.email, body.code, body.new_password)
    except auth.AuthError as exc:
        raise _refused(db, exc) from exc
    db.commit()
    return token_for(user)


@router.post("/password/change", response_model=TokenResponse)
def change_password(body: ChangePasswordRequest, db: DbSession, user: CurrentUser) -> TokenResponse:
    """New password while signed in; other sessions are signed out, this one gets a new token."""
    if not verify_password(body.current_password, user.password_hash):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Your current password is not right.")
    try:
        auth.check_password(body.new_password)
    except auth.AuthError as exc:
        raise HTTPException(exc.status, exc.message) from exc
    auth.set_password(user, body.new_password)
    db.commit()
    return token_for(user)


@router.get("/me", response_model=UserOut)
def me(user: CurrentUser, request: Request) -> UserOut:
    out = user_out(user)
    owner: User | None = getattr(request.state, "acting_owner", None)
    if owner is not None:
        out.viewed_by_owner = owner.email
    return out

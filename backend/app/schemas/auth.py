from pydantic import BaseModel, ConfigDict, Field

from app.models import Role


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    full_name: str
    role: Role
    org_id: str
    org_name: str
    is_owner: bool = False  # the product owner (settings owner_emails)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class SignupRequest(BaseModel):
    full_name: str = Field(min_length=1, max_length=200)
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(max_length=128)
    company: str | None = Field(default=None, max_length=200)  # optional: else the email


class EmailRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)


class VerifyEmailRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    code: str = Field(min_length=1, max_length=12)


class ResetPasswordRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    code: str = Field(min_length=1, max_length=12)
    new_password: str = Field(max_length=128)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(max_length=128)
    new_password: str = Field(max_length=128)


class CodeSent(BaseModel):
    """A code was emailed (or, for a reset, would be if the account exists)."""

    email: str
    message: str

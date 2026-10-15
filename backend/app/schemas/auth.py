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


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut

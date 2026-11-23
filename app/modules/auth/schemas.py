from typing import Annotated
from uuid import UUID

from pydantic import AfterValidator, BaseModel, EmailStr, Field, StringConstraints

from app.core.constants import PASSWORD_MAX_LENGTH
from app.core.security import validate_password_strength
from app.modules.users.schemas import UserResponse

# Emails are stored/looked up lower-cased
NormalizedEmail = Annotated[EmailStr, AfterValidator(lambda v: v.lower())]
# Names are trimmed (passwords are NEVER trimmed)
Name = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)
]


class RegisterRequest(BaseModel):
    full_name: Name
    email: NormalizedEmail
    password: Annotated[str, AfterValidator(validate_password_strength)]


class LoginRequest(BaseModel):
    email: NormalizedEmail
    # No strength check on login; max length only protects Argon2 from huge inputs
    password: str = Field(min_length=1, max_length=PASSWORD_MAX_LENGTH)

class AuthResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse
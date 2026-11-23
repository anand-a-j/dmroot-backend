from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import AfterValidator, BaseModel, EmailStr, StringConstraints

from app.core.security import validate_password_strength

# Reusable field types (used by auth and users requests)
NormalizedEmail = Annotated[
    EmailStr, AfterValidator(lambda v: v.lower())
]  # stored lower-cased
Name = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)
]
StrongPassword = Annotated[
    str, AfterValidator(validate_password_strength)
]


class UserResponse(BaseModel):
    id: UUID
    full_name: str
    email: str
    role: str
    org_id: UUID | None
    status: str
    email_verified_at: datetime | None
    created_at: datetime


class CurrentUser(UserResponse):
    """The authenticated caller, loaded fresh from the database on every request."""

    org_status: str | None = None  # internal only; /auth/me returns UserResponse


# initial password; the admin shares it with the member
class CreateMemberRequest(BaseModel):
    full_name: Name
    email: NormalizedEmail
    password: StrongPassword  
"""
Reusable FastAPI dependencies for authentication and authorization.

Chain:
    token
      -> get_current_user
      -> get_current_active_user
      -> require_role(...)

Every request re-checks the user against the database.
Suspended users and demoted roles are blocked immediately.
"""

from typing import Annotated

from fastapi import Depends
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
)

from app.core.database import get_pool
from app.core.enum.user_role import UserRole
from app.core.exceptions import (
    ForbiddenException,
    UnauthorizedException,
)
from app.core.security import decode_access_token
from app.modules.users import repository as users_repo
from app.modules.users.schemas import CurrentUser

# Security scheme

# Handle missing credentials ourselves with a custom 401.
bearer_scheme = HTTPBearer(auto_error=False)


# Authentication
async def get_current_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(bearer_scheme),
    ],
) -> CurrentUser:
    """Validate access token and fetch the user from database."""

    if credentials is None:
        raise UnauthorizedException("Authentication required")

    user_id = decode_access_token(credentials.credentials)

    row = await users_repo.get_by_id(
        get_pool(),
        user_id=user_id,
    )

    if row is None:
        raise UnauthorizedException("Invalid access token")

    return CurrentUser.model_validate(dict(row))


# Account and organization status
async def get_current_active_user(
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> CurrentUser:
    """Ensure user account and organization are active."""

    if user.status != "active":
        raise ForbiddenException("This account is not active")

    if user.org_status != "active":
        raise ForbiddenException("This organization is not active")

    return user


# Role-based authorization


def require_role(*allowed_roles: str):
    """Allow access only to the specified roles."""

    async def dependency(
        user: Annotated[
            CurrentUser,
            Depends(get_current_active_user),
        ],
    ) -> CurrentUser:

        if user.role not in allowed_roles:
            raise ForbiddenException(
                "You do not have permission to perform this action"
            )

        return user

    return dependency


# Role-specific authorization dependencies

require_platform_admin = require_role(
    UserRole.PLATFORM_ADMIN.value,
)

require_admin = require_role(
    UserRole.ADMIN.value,
)

CurrentUserDep = Annotated[
    CurrentUser,
    Depends(get_current_active_user),
]

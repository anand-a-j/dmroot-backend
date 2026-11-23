"""Reusable FastAPI dependencies for authentication and authorization.

Chain: token -> get_current_user -> get_current_active_user -> require_role(...)
Everything is re-checked against the database on every request, so a
suspended user or a demoted role is blocked immediately.
"""

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.constants import ROLE_PLATFORM_ADMIN
from app.core.database import get_pool
from app.core.exceptions import ForbiddenException, UnauthorizedException
from app.core.security import decode_access_token
from app.modules.users import repository as users_repo
from app.modules.users.schemas import CurrentUser

# auto_error=False so a missing header gives our own 401, not FastAPI's default
bearer_scheme = HTTPBearer(auto_error=False)





async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> CurrentUser:
    """Valid token + the user still exists. Does NOT check account status."""
    if credentials is None:
        raise UnauthorizedException("Authentication required")

    user_id = decode_access_token(credentials.credentials)
    row = await users_repo.get_by_id(get_pool(), user_id=user_id)
    if row is None:
        raise UnauthorizedException("Invalild access token")
    return CurrentUser.model_validate(dict(row))


async def get_current_active_user(
    user: CurrentUser = Depends(get_current_user),
) -> CurrentUser:
    """Use this for almost every endpoint: account AND organization must be active."""
    if user.status != "active":
        raise ForbiddenException("This account is not active")
    if user.role != ROLE_PLATFORM_ADMIN and user.org_status != "active":
        raise ForbiddenException("This organization is not active")
    return user


def require_role(*allowed_roles: str):
    """Allow only the listed roles; everything else gets 403 (default deny).

    Usage: admin: CurrentUser = Depends(require_role(ROLE_ADMIN))
    """

    async def dependency(
        user: CurrentUser = Depends(get_current_active_user),
    ) -> CurrentUser:
        if user.role not in allowed_roles:
            raise ForbiddenException(
                "You do not have permission to perform this action"
            )
        return user

    return dependency


# Shortcut for platform-owner-only endpoints
require_platform_admin = require_role(ROLE_PLATFORM_ADMIN)

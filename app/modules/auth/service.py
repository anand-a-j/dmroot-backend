import logging
from uuid import UUID, uuid4

import asyncpg

from app.core.config import settings
from app.core.constants import ROLE_ADMIN, ROLE_PLATFORM_ADMIN
from app.core.database import DBExecutor, get_pool, transaction
from app.core.exceptions import (
    ConflictException,
    ForbiddenException,
    UnauthorizedException,
)
from app.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    refresh_token_expiry,
    verify_dummy_password,
    verify_password,
)
from app.modules.auth import repository as auth_repo
from app.modules.auth.schemas import AuthResponse, LoginRequest, RegisterRequest
from app.modules.organizations import repository as orgs_repo
from app.modules.users import repository as users_repo
from app.modules.users.schemas import UserResponse

logger = logging.getLogger(__name__)


def _class_user_agent(user_agent: str | None) -> str | None:
    return (user_agent or "")[:255] or None


async def _issue_tokens(
    db: DBExecutor,
    *,
    user_id: UUID,
    user_agent: str | None,
    family_id: UUID | None = None,
) -> dict:
    """Create an access token + a new refresh token row."""

    refresh_token = generate_refresh_token()

    await auth_repo.create_refresh_token(
        db,
        user_id=user_id,
        family_id=family_id or uuid4(),
        token_hash=hash_refresh_token(refresh_token),
        expires_at=refresh_token_expiry(),
        user_agent=_class_user_agent(user_agent),
    )

    return {
        "access_token": create_access_token(user_id),
        "refresh_token": refresh_token,
        "expires_in": settings.access_token_expire_minutes * 60,
    }


async def register(payload: RegisterRequest, *, user_agent: str | None) -> AuthResponse:
    # Hash BEFORE opening the transaction: hashing is slow and we don't want
    # to hold a database connection while it runs.
    password_hash = await hash_password(payload.password)
    user_id = uuid4()

    try:
        # One transaction: user + organization + roles + membership + session.
        # If anything fails, nothing is saved
        async with transaction() as conn:
            org_id = await orgs_repo.create_organization(conn, payload.full_name)
            user = await users_repo.create_user(
                conn,
                user_id=user_id,
                full_name=payload.full_name,
                email=payload.email,
                password_hash=password_hash,
                org_id=org_id,
                role=ROLE_ADMIN,
            )
            tokens = await _issue_tokens(conn, user_id=user_id, user_agent=user_agent)
    except asyncpg.UniqueViolationError:
        # The unique index decides, so two simultaneous signups can't both win.
        raise ConflictException("An account with this email already exists") from None
    logger.info("User registered user_id=%s org_id=%s", user_id, org_id)
    return AuthResponse(
        **tokens, user=UserResponse.model_validate(dict(user)), org_id=org_id
    )


async def login(payload: LoginRequest, *, user_agent: str | None) -> AuthResponse:
    db = get_pool()
    user = await users_repo.get_by_email(db, payload.email)

    # Same error and similar timing for "unknown email" and "wrong password",
    # so attackers can't discover which emails are registered.
    if user is None:
        await verify_dummy_password(payload.password)
        raise UnauthorizedException("Invalid email or password")
    if not await verify_password(payload.password, user["password_hash"]):
        raise UnauthorizedException("Invalid email or password")

    # Status is checked only AFTER the password is proven correct.
    if user["status"] != "active":
        raise ForbiddenException("This account is not active")

    if user["org_id"] is None:
        raise ForbiddenException("User is not associated with an organization")

    tokens = await _issue_tokens(db, user_id=user["id"], user_agent=user_agent)

    logger.info("User logged in user_id=%s", user["id"])
    return AuthResponse(
        **tokens, user=UserResponse.model_validate(dict(user)), org_id=user["org_id"]
    )

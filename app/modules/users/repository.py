from uuid import UUID

import asyncpg

from app.core.database import DBExecutor
from app.modules.users.schemas import UserResponse

# Safe-to-expose columns (password_hash is added only where login needs it).
# org_status lets callers block users whose organization is suspended/deleted.
_COLUMNS = """
    u.id, u.full_name, u.email, u.role, u.org_id, u.status,
    u.email_verified_at, u.created_at, o.status AS org_status
"""
_FROM = """
    FROM users u
    LEFT JOIN organizations o ON o.id = u.org_id AND o.deleted_at IS NULL
"""


async def get_by_email(db: DBExecutor, email: str) -> asyncpg.Record | None:
    """Login lookup (includes password_hash). `email` must be lower-cased."""
    return await db.fetchrow(
        "SELECT "
        + _COLUMNS
        + ", u.password_hash "
        + _FROM
        + " WHERE lower(u.email) = $1 AND u.deleted_at IS NULL",
        email,
    )


async def get_by_id(db: DBExecutor, user_id: UUID) -> asyncpg.Record | None:
    """Per-request lookup used by auth dependencies (no password_hash)."""
    return await db.fetchrow(
        "SELECT " + _COLUMNS + _FROM + " WHERE u.id = $1 AND u.deleted_at IS NULL",
        user_id,
    )


async def create_user(
    db: DBExecutor,
    *,
    user_id: UUID,
    org_id: UUID | None,
    role: str,
    full_name: str,
    email: str,
    password_hash: str,
) -> UserResponse:
    """Create a user and return the public user representation."""

    row = await db.fetchrow(
        """
        INSERT INTO users (
            id, org_id, role, full_name, email, password_hash,
            status, created_at, updated_at
        )
        VALUES ($1, $2, $3, $4, $5, $6, 'active', NOW(), NOW())
        RETURNING
            id, full_name, email, role, org_id, status,
            email_verified_at, created_at
        """,
        user_id,
        org_id,
        role,
        full_name,
        email,
        password_hash,
    )

    if row is None:
        raise RuntimeError("Failed to create user")

    return UserResponse.model_validate(dict(row))

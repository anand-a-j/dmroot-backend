"""
Raw SQL for connected_accounts.

Rules:
- Every query filters by org_id (tenant isolation).
- All queries use _COLUMNS, which never includes access_token_encrypted.
  The only function that returns the token ciphertext is get_encrypted_token().
- Functions take a connection; the service owns transactions.
- f-strings only inject the constant _COLUMNS. All values are $n parameters.
"""

from typing import Any
from uuid import UUID

from app.core.database import DBExecutor
from app.core.mappers import record_to_dict
from app.modules.connected_accounts.schema import ConnectedAccountResponse
from app.modules.users.schemas import UserResponse

Account = dict[str, Any]

_COLUMNS = """
    id, org_id, connected_by_user_id, platform, platform_account_id,
    account_name, username, token_expires_at, status, disconnected_at,
    metadata, created_at, updated_at
"""


async def get_by_id(
    db: DBExecutor,
    org_id: UUID,
    account_id: UUID,
) -> ConnectedAccountResponse | None:
    row = await db.fetchrow(
        f"""
        SELECT {_COLUMNS}
        FROM connected_accounts
        WHERE id = $1 AND org_id = $2
        """,
        account_id,
        org_id,
    )

    if row is None:
        return None

    return ConnectedAccountResponse.model_validate(record_to_dict(row))


async def lock_by_id(
    db: DBExecutor,
    org_id: UUID,
    account_id: UUID,
) -> ConnectedAccountResponse | None:
    """Fetch and lock the account row inside a transaction."""

    row = await db.fetchrow(
        f"""
        SELECT {_COLUMNS}
        FROM connected_accounts
        WHERE id = $1 AND org_id = $2
        FOR UPDATE
        """,
        account_id,
        org_id,
    )

    if row is None:
        return None

    return ConnectedAccountResponse.model_validate(record_to_dict(row))


async def lock_for_connect(
    db: DBExecutor,
    organization_id: UUID,
    platform: str,
    platform_account_id: str,
) -> Account | None:
    """This organization's existing row (any status) for an external account, locked."""
    row = await db.fetchrow(
        f"""
        SELECT {_COLUMNS}
        FROM connected_accounts
        WHERE organization_id = $1
          AND platform = $2
          AND platform_account_id = $3
        ORDER BY created_at
        LIMIT 1
        FOR UPDATE
        """,
        organization_id,
        platform,
        platform_account_id,
    )
    return record_to_dict(row)


async def find_live_owner_org_id(
    db: DBExecutor,
    platform: str,
    platform_account_id: str,
) -> UUID | None:
    """Organization that currently holds this external account (active or expired).

    Deliberately cross-tenant: used only to detect a conflict, returns the ID only.
    """
    return await db.fetchval(
        """
        SELECT organization_id
        FROM connected_accounts
        WHERE platform = $1
          AND platform_account_id = $2
          AND status <> 'disconnected'
        """,
        platform,
        platform_account_id,
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


async def mark_expired(
    db: DBExecutor,
    org_id: UUID,
    account_id: UUID,
) -> Account | None:
    """active -> expired. Returns None if the row is not currently active."""
    row = await db.fetchrow(
        f"""
        UPDATE connected_accounts
        SET status = 'expired'
        WHERE id = $1 AND org_id = $2 AND status = 'active'
        RETURNING {_COLUMNS},
        """,
        account_id,
        org_id,
    )
    return record_to_dict(row)


async def mark_disconnected(
    db: DBExecutor,
    org_id: UUID,
    account_id: UUID,
) -> ConnectedAccountResponse | None:
    """Disconnect account and return the updated account."""

    row = await db.fetchrow(
        f"""
        UPDATE connected_accounts
        SET status = 'disconnected',
            access_token_encrypted = NULL,
            token_expires_at = NULL,
            disconnected_at = NOW()
        WHERE id = $1
          AND org_id = $2
          AND status <> 'disconnected'
        RETURNING {_COLUMNS}
        """,
        account_id,
        org_id,
    )

    if row is None:
        return None

    return ConnectedAccountResponse.model_validate(record_to_dict(row))


async def get_encrypted_token(
    db: DBExecutor,
    org_id: UUID,
    account_id: UUID,
) -> str | None:
    """INTERNAL. The only function that reads the token ciphertext.

    Active accounts only. Callers must decrypt briefly in memory and never
    log, cache, enqueue or return the result.
    """
    return await db.fetchval(
        """
        SELECT access_token_encrypted
        FROM connected_accounts
        WHERE id = $1 AND org_id = $2 AND status = 'active'
        """,
        account_id,
        org_id,
    )

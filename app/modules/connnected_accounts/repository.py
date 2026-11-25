"""
Raw SQL for connected_accounts.

Rules:
- Every query filters by org_id (tenant isolation).
- All queries use _COLUMNS, which never includes access_token_encrypted.
  The only function that returns the token ciphertext is get_encrypted_token().
- Functions take a connection; the service owns transactions.
- f-strings only inject the constant _COLUMNS. All values are $n parameters.
"""

import json
from datetime import datetime
from typing import Any
from uuid import UUID

from app.core.database import DBExecutor
from app.core.enum.platform import Platform
from app.core.mappers import record_to_dict

Account = dict[str, Any]

_COLUMNS = """
    id, org_id, connected_by_user_id, platform, platform_account_id,
    account_name, username, token_expires_at, status, disconnected_at,
    metadata, created_at, updated_at
"""


async def list_by_org(
    db: DBExecutor, org_id: UUID, platform: Platform | None = None
) -> list[Account]:
    rows = await db.fetch(
        f"""
        SELECT {_COLUMNS}
        FROM connected_accounts
        WHERE organization_id = $1
          AND ($2::text IS NULL OR platform = $2::text)
        ORDER BY created_at DESC
        """,
        org_id,
        platform,
    )
    return [record_to_dict(r) for r in rows]


async def lock_by_id(
    db: DBExecutor,
    organization_id: UUID,
    account_id: UUID,
) -> Account | None:
    """Like get_by_id but locks the row. Call inside a transaction."""
    row = await db.fetchrow(
        f"""
        SELECT {_COLUMNS}
        FROM connected_accounts
        WHERE id = $1 AND organization_id = $2
        FOR UPDATE
        """,
        account_id,
        organization_id,
    )
    return record_to_dict(row)


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


async def insert(
    db: DBExecutor,
    *,
    account_id: UUID,
    organization_id: UUID,
    connected_by_user_id: UUID | None,
    platform: str,
    platform_account_id: str,
    account_name: str | None,
    username: str | None,
    access_token_encrypted: str,
    token_expires_at: datetime | None,
    metadata: dict[str, Any],
) -> Account:
    row = await db.fetchrow(
        f"""
        INSERT INTO connected_accounts(
        id, org_id, connected_by_user_id, platform,
        platform_account_id, account_name, username,
        access_token_encrypted, token_expires_at, status, metadata
        )
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, 'active', $10::text::jsonb)
        RETURNING {_COLUMNS}

        """,
        account_id,
        organization_id,
        connected_by_user_id,
        platform,
        platform_account_id,
        account_name,
        username,
        access_token_encrypted,
        token_expires_at,
        json.dumps(metadata),
    )
    return record_to_dict(row)


async def reconnect(
    db: DBExecutor,
    *,
    org_id: UUID,
    account_id: UUID,
    connected_by_user_id: UUID | None,
    account_name: str | None,
    username: str | None,
    access_token_encrypted: str,
    token_expires_at: datetime | None,
    metadata: dict[str, Any],
) -> Account | None:
    row = await db.fetchrow(
        f"""
        UPDATE connected_accounts
        SET connected_by_user_id = $3,
            account_name = $4,
            username = $5,
            access_token_encrypted = $6,
            token_expires_at = $7,
            metadata = $8::text::jsonb,
            status = 'active',
            disconnecte_at = NULL
        WHERE id = $1 AND org_id = $2
        RETURNING {_COLUMNS}
        """,
        account_id,
        org_id,
        connected_by_user_id,
        account_name,
        username,
        access_token_encrypted,
        token_expires_at,
        json.dumps(metadata),
    )
    return record_to_dict(row)


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
) -> Account | None:
    """Keep the row, drop the token. Returns None if already disconnected."""
    row = await db.fetchrow(
        f"""
        UPDATE connected_accounts
        SET status = 'disconnected',
            access_token_encrypted = NULL,
            token_expires_at = NULL,
            disconnected_at = NOW()
        WHERE id = $1 AND org_id = $2 AND status <> 'disconnected'
        RETURNING {_COLUMNS}
        """,
        account_id,
        org_id,
    )
    return record_to_dict(row)


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
        org_id
    )

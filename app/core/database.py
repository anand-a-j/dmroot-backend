"""PostgreSQL connection pool (asyncpg) and transaction helper.

- One pool for the whole app, created at startup and closed at shutdown.
- Repositories accept a `DBExecutor` (pool OR connection), so the same
  repository function works for a single query or inside a transaction.
- Use `transaction()` in services when several writes must succeed together.
"""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import TypeAlias, cast

import asyncpg

from app.core.config import settings
from app.core.constants import DEFAULT_REQUEST_TIMEOUT

logger = logging.getLogger(__name__)


# Anything that has fetch / fetchrow / fetchval / execute
DBExecutor: TypeAlias = asyncpg.Pool | asyncpg.Connection

_pool: asyncpg.Pool | None = None


async def init_pool() -> None:
    """Create the pool once at application startup."""
    global _pool
    if _pool is not None:
        return
    _pool = await asyncpg.create_pool(
        dsn=settings.database_dsn,
        min_size=settings.db_pool_min_size,
        max_size=settings.db_pool_max_size,
        command_timeout=DEFAULT_REQUEST_TIMEOUT,
    )
    logger.info("Database pool initialised")


async def close_pool() -> None:
    """Close the pool at application shutdown."""
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None
        logger.info("Database pool closed")


def get_pool() -> asyncpg.Pool:
    """Return the pool. Also usable directly as a FastAPI dependency: Depends(get_pool)."""
    if _pool is None:
        raise RuntimeError("Database pool is not initialised")
    return _pool


@asynccontextmanager
async def transaction() -> AsyncGenerator[asyncpg.Connection, None]:
    """Run several queries in ONE transaction (commit on success, rollback on error)."""
# 799: Need to verify conn.transaction()
    async with get_pool().acquire() as conn, conn.transaction():
        yield cast(asyncpg.Connection, conn)

from datetime import datetime
from uuid import UUID, uuid4

from app.core.database import DBExecutor


async def create_refresh_token(
    db: DBExecutor,
    *,
    user_id: UUID,
    family_id: UUID,
    token_hash: str,
    expires_at: datetime,
    user_agent: str | None,
) -> None:
    await db.execute(
        """
        INSERT INTO refresh_tokens (id, user_id, family_id, token_hash,
                                    expires_at, user_agent, created_at)
        VALUES ($1, $2, $3, $4, $5, $6, NOW())       
        """,
        uuid4(),
        user_id,
        family_id,
        token_hash,
        expires_at,
        user_agent,
    )

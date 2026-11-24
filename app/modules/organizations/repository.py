from uuid import UUID, uuid4

from app.core.database import DBExecutor


async def create_organization(db: DBExecutor, name: str) -> UUID:
    org_id = uuid4()
    await db.execute(
        """
        INSERT INTO organizations (id, name, status, created_at, updated_at)
        VALUES ($1, $2, 'active', NOW(), NOW())
        """,
        org_id,
        name,
    )
    return org_id

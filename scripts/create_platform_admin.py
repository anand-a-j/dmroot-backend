import asyncio
from uuid import uuid4

from app.core.database import get_pool, init_pool
from app.core.security import hash_password


async def main():
    email = input("Admin email: ").strip().lower()
    name = input("Admin name: ").strip()
    password = input("Admin password: ")

    password_hash = await hash_password(password)

    await init_pool()

    pool = await get_pool()

    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO users (
                id, org_id, full_name, email,
                password_hash, role, status
            )
            VALUES ($1, NULL, $2, $3, $4, 'platform_admin', 'active')
            """,
            uuid4(),
            name,
            email,
            password_hash,
        )

    print("Platform admin created.")


if __name__ == "__main__":
    asyncio.run(main())

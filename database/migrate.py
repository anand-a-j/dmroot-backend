"""Migration runner. Run from the project root:

python -m database.migrate up
python -m database.migrate status
"""

import asyncio
import hashlib
import re
import sys
from pathlib import Path
from typing import NamedTuple

import asyncpg

MIGRATIONS_DIR = Path(__file__).parent / "migrations"
FILENAME_RE = re.compile(r"^(\d{4})_[a-z0-9_]+\.sql$")
ADVISORY_LOCK_KEY = 7_204_001  # arbitrary constant, unique to DMRoot migrations

CREATE_TRACKING_TABLE = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    version    TEXT PRIMARY KEY,
    checksum   TEXT NOT NULL,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
)
"""


class MigrationError(Exception):
    """Raised for any migration problem that must stop the run."""


class Migration(NamedTuple):
    version: str  # filename without .sql, e.g. "0002_users_create_users"
    checksum: str
    sql: str


def get_dsn() -> str:
    from app.core.config import settings

    return settings.database_dsn


def load_migrations() -> list[Migration]:
    migrations: list[Migration] = []
    seen_numbers: set[str] = set()

    for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
        match = FILENAME_RE.match(path.name)
        if match is None:
            raise MigrationError(f"Invalid migration filename: {path.name}")
        number = match.group(1)
        if number in seen_numbers:
            raise MigrationError(f"Duplicate migration number: {number}")
        seen_numbers.add(number)

        sql = path.read_text(encoding="utf-8")
        checksum = hashlib.sha256(sql.encode("utf-8")).hexdigest()
        migrations.append(Migration(path.stem, checksum, sql))

    return migrations


async def fetch_applied(conn: asyncpg.Connection) -> dict[str, str]:
    rows = await conn.fetch(
        "SELECT version, checksum FROM schema_migrations ORDER BY version"
    )
    return {row["version"]: row["checksum"] for row in rows}


def find_pending(
    migrations: list[Migration], applied: dict[str, str]
) -> list[Migration]:
    """Validate history is intact and return migrations still to run."""
    by_version = {m.version: m for m in migrations}

    for version, checksum in applied.items():
        migration = by_version.get(version)
        if migration is None:
            raise MigrationError(f"Applied migration missing on disk: {version}")
        if migration.checksum != checksum:
            raise MigrationError(
                f"Applied migration was modified: {version}. "
                "Never edit applied migrations; create a new one."
            )

    pending = [m for m in migrations if m.version not in applied]
    if applied and pending and pending[0].version < max(applied):
        raise MigrationError(f"Out-of-order migration: {pending[0].version}")
    return pending


async def run_up() -> None:
    migrations = load_migrations()
    conn = await asyncpg.connect(get_dsn())
    try:
        # Session-level lock: released automatically when the connection closes.
        locked = await conn.fetchval(
            "SELECT pg_try_advisory_lock($1)", ADVISORY_LOCK_KEY
        )
        if not locked:
            raise MigrationError("Another migration process is already running")

        await conn.execute(CREATE_TRACKING_TABLE)
        pending = find_pending(migrations, await fetch_applied(conn))
        if not pending:
            print("No pending migrations.")
            return

        for migration in pending:
            print(f"Applying {migration.version} ...")
            async with conn.transaction():  # all-or-nothing per migration
                await conn.execute(migration.sql)
                await conn.execute(
                    "INSERT INTO schema_migrations (version, checksum) VALUES ($1, $2)",
                    migration.version,
                    migration.checksum,
                )
        print(f"Applied {len(pending)} migration(s).")
    finally:
        await conn.close()


async def run_status() -> None:
    migrations = load_migrations()
    conn = await asyncpg.connect(get_dsn())
    try:
        table_exists = await conn.fetchval(
            "SELECT to_regclass('schema_migrations') IS NOT NULL"
        )
        applied = await fetch_applied(conn) if table_exists else {}
        for migration in migrations:
            state = "applied" if migration.version in applied else "pending"
            print(f"[{state}] {migration.version}")
    finally:
        await conn.close()


def main() -> None:
    commands = {"up": run_up, "status": run_status}
    if len(sys.argv) != 2 or sys.argv[1] not in commands:
        print("Usage: python -m database.migrate [up|status]")
        sys.exit(2)
    try:
        asyncio.run(commands[sys.argv[1]]())
    except MigrationError as exc:
        print(f"Migration error: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()

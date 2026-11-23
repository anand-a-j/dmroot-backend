# DMRoot Database

PostgreSQL 18 · asyncpg · raw SQL · no ORM.

## Commands (run from the project root)
```
python -m database.migrate status   # list applied/pending
python -m database.migrate up       # apply pending migrations
```
Migrations never run automatically on app startup.

## Rules
1. Migrations are plain `.sql` files in `database/migrations/`.
2. Name: `NNNN_module_description.sql` (e.g. `0002_users_create_users.sql`).
3. Applied migrations are immutable. The runner stops if a checksum changes. Fix mistakes with a new migration.
4. Each migration runs in one transaction, in order.
5. An advisory lock prevents two runners at once.
6. Applied versions are stored in `schema_migrations`.

## Add a migration
1. Take the next free number.
2. Write the SQL (to change a function, use `CREATE OR REPLACE`).
3. Run `status`, then `up`.
4. Commit the file.

## Inspect current state (psql)
`\d users` · `\df` · `\d+ users`

Optional snapshot (generated, never hand-edited):
`pg_dump --schema-only --no-owner dmroot > database/docs/schema.sql`

## Data rules
- Emails stored lowercase (DB enforced; service normalizes).
- Soft delete via `deleted_at`; always filter `deleted_at IS NULL`.
- `updated_at` is maintained by a trigger.
- Runtime SQL lives in `database/queries/`, executed only from repositories.
- Never log the DSN or any password.
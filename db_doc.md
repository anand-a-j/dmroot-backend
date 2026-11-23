# DMRoot Database Conventions

Place at `database/docs/conventions.md`. Follow these for every table, column and migration.

## 1. Naming

| Item | Rule | Example |
|---|---|---|
| General | lowercase `snake_case`, English, no spaces, no quotes | `workspace_members` |
| Table | plural noun | `users`, `automations` |
| Join table | both names | `workspace_members` |
| Column | singular noun | `full_name` |
| Primary key | `id` | `id` |
| Foreign key | `<singular_table>_id` | `workspace_id` |
| Timestamp | ends with `_at` | `created_at`, `deleted_at` |
| Boolean | starts with `is_` / `has_` | `is_active` |
| Primary key constraint | `pk_<table>` | `pk_users` |
| Foreign key constraint | `fk_<table>_<column>` | `fk_automations_workspace_id` |
| Unique constraint/index | `uq_<table>_<columns>` | `uq_users_email` |
| Check constraint | `ck_<table>_<column>` | `ck_users_status` |
| Index | `idx_<table>_<columns>` | `idx_automations_workspace_id` |
| Function | `verb_noun` | `set_updated_at` |
| Trigger | `trg_<table>_<action>` | `trg_users_set_updated_at` |
| View | `v_<name>` | `v_active_users` |
| Migration file | `NNNN_<module>_<action>_<object>.sql` | `0002_users_create_users.sql` |

Migration actions: `create`, `add`, `alter`, `drop`, `backfill`.

Never use reserved words as names (`user`, `order`, `group`, `table`, `check`). That is why the table is `users`.

## 2. Table Template

```sql
CREATE TABLE workspaces (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        VARCHAR(100) NOT NULL,
    owner_id    UUID NOT NULL REFERENCES users (id) ON DELETE RESTRICT,
    status      VARCHAR(20) NOT NULL DEFAULT 'active',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at  TIMESTAMPTZ,
    CONSTRAINT ck_workspaces_status CHECK (status IN ('active', 'inactive', 'suspended'))
);

CREATE INDEX idx_workspaces_owner_id ON workspaces (owner_id);
```

Every table has `id`, `created_at`, `updated_at`. Add `deleted_at` only where soft delete is needed.

## 3. Data Types

| Data | Type |
|---|---|
| IDs | `UUID` |
| Short text with a limit | `VARCHAR(n)` |
| Long text, tokens, hashes | `TEXT` |
| Dates and times | `TIMESTAMPTZ` (never `TIMESTAMP`) |
| True/false | `BOOLEAN` |
| Money | `NUMERIC(12,2)` (never `FLOAT`) |
| Counters | `INTEGER` / `BIGINT` |
| Flexible data (e.g. webhook payloads) | `JSONB` |
| Fixed choices (status, role) | `VARCHAR` + `CHECK` (not Postgres `ENUM`) |
| Instagram / Meta IDs | `TEXT` (external IDs are strings) |

## 4. Rules

**Do**
- Make columns `NOT NULL` by default. Allow `NULL` only with a clear reason.
- Add `workspace_id UUID NOT NULL` (with foreign key and index) to every tenant-owned table.
- Index every foreign key column and every column used often in `WHERE` or `ORDER BY`.
- Choose `ON DELETE` explicitly on every foreign key: `RESTRICT` by default, `CASCADE` only for child rows that cannot exist without the parent.
- Use `CHECK` constraints for allowed values.
- Use a partial unique index when combining unique values with soft delete:
  `CREATE UNIQUE INDEX uq_users_email ON users (lower(email)) WHERE deleted_at IS NULL;`
- Store only `password_hash`. Encrypt access tokens before storing.

**Don't**
- Don't create or change tables by hand. Use migrations only.
- Don't edit a migration that has already run.
- Don't add indexes "just in case". Each index slows writes.
- Don't store plain passwords or plain tokens.
- Don't use `SELECT *` in application queries. List the columns.
- Don't store lists as comma-separated text. Use a child table or `JSONB`.

## 5. Migration Rules

- One purpose per migration. Each runs in one transaction.
- Wrong something that already ran? Write a new migration. Never edit the old one.
- Safe changes: new table, new nullable column, new index.
- Risky changes (drop column, rename, change type, add `NOT NULL` to a column with data): do in small steps across several migrations.
- Use plain `CREATE INDEX`. `CREATE INDEX CONCURRENTLY` cannot run inside a transaction.
- Before committing: run all migrations on an empty database and confirm they pass.

## 6. New Table Checklist

1. Name follows section 1.
2. Has `id`, `created_at`, `updated_at` (and `deleted_at` if needed).
3. Has `workspace_id` if tenant-owned.
4. Every foreign key has `ON DELETE` and an index.
5. Allowed values enforced with `CHECK`.
6. `updated_at` trigger added.
7. Migration file named and numbered correctly.
8. `database/docs/schema-overview.md` updated in the same commit.

## 7. Schema Overview Entry (copy for each table)

```md
### users
Purpose: platform accounts.
Key columns: id, email (unique), password_hash, status.
Relationships: owns workspaces (workspaces.owner_id).
Migration: 0002_users_create_users.sql
```
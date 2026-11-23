CREATE TABLE users (
    id UUID PRIMARY KEY,

    org_id UUID REFERENCES organizations(id)
        ON DELETE RESTRICT,

    full_name VARCHAR(100) NOT NULL,
    email VARCHAR(255) NOT NULL,
    password_hash TEXT NOT NULL,

    role VARCHAR(30) NOT NULL DEFAULT 'member',
    status VARCHAR(20) NOT NULL DEFAULT 'active',

    email_verified_at TIMESTAMPTZ,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,

    CONSTRAINT users_email_unique UNIQUE (email),

    CONSTRAINT users_role_check
        CHECK (role IN ('platform_admin', 'admin', 'member')),

    CONSTRAINT users_status_check
        CHECK (status IN ('active', 'inactive', 'suspended', 'deleted'))
);

CREATE INDEX idx_users_org_id
    ON users(org_id);

CREATE INDEX idx_users_org_status
    ON users(org_id, status);

CREATE TRIGGER trg_users_updated_at
BEFORE UPDATE ON users
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();
CREATE TABLE connected_accounts (
    id UUID PRIMARY KEY,

    org_id UUID NOT NULL
        REFERENCES organizations(id) ON DELETE CASCADE,

    connected_by_user_id UUID
        REFERENCES users(id) ON DELETE SET NULL,

    platform VARCHAR(30) NOT NULL,
    platform_account_id VARCHAR(100) NOT NULL,
    account_name VARCHAR(150),
    username VARCHAR(100),

    access_token_encrypted TEXT,
    token_expires_at TIMESTAMPTZ,

    status VARCHAR(20) NOT NULL DEFAULT 'active',
    disconnected_at TIMESTAMPTZ,

    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT connected_accounts_status_check
        CHECK (status IN ('active', 'expired', 'disconnected')),

    CONSTRAINT connected_accounts_platform_account_id_check
        CHECK (length(btrim(platform_account_id)) > 0),

    -- A disconnected row holds no token and no expiry; every other row must
    -- hold a token. disconnected_at is set exactly when status = 'disconnected'.
    CONSTRAINT connected_accounts_state_check
        CHECK (
            (
                status = 'disconnected'
                AND access_token_encrypted IS NULL
                AND token_expires_at IS NULL
                AND disconnected_at IS NOT NULL
            )
            OR
            (
                status <> 'disconnected'
                AND access_token_encrypted IS NOT NULL
                AND disconnected_at IS NULL
            )
        ),

    CONSTRAINT connected_accounts_metadata_object_check
        CHECK (jsonb_typeof(metadata) = 'object')
);

-- One live (active or expired) connection per external account across ALL
-- organizations. Also serves webhook/message lookups by platform account.
CREATE UNIQUE INDEX uq_connected_accounts_live_platform_account
    ON connected_accounts (platform, platform_account_id)
    WHERE status <> 'disconnected';

-- Listing an organization's accounts, optionally by platform.
CREATE INDEX idx_connected_accounts_org_platform
    ON connected_accounts (organization_id, platform);

-- Future token-refresh job: "which active tokens expire soon?"
CREATE INDEX idx_connected_accounts_active_token_expiry
    ON connected_accounts (token_expires_at)
    WHERE status = 'active';

CREATE TRIGGER trg_connected_accounts_updated_at
BEFORE UPDATE ON connected_accounts
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

COMMENT ON TABLE connected_accounts IS
    'External messaging accounts (e.g. Instagram) connected by an organization. Holds encrypted access tokens.';

COMMENT ON COLUMN connected_accounts.platform_account_id IS
    'External account ID as text. Must equal the ID Meta sends in webhooks (verify in Phase 6).';

COMMENT ON COLUMN connected_accounts.access_token_encrypted IS
    'Ciphertext only (Fernet). Never select by default; only the dedicated repository method may read it. NULL only when disconnected.';

COMMENT ON COLUMN connected_accounts.status IS
    'active | expired | disconnected. disconnected -> active only through a reconnect upsert in the service.';

COMMENT ON COLUMN connected_accounts.metadata IS
    'Display-only JSON object for the UI (e.g. profile picture URL). No secrets. Never filtered on.';
-- Provisioning for NEW disposable test databases only. No production execution.
-- Reset HTTP routes remain disabled on PostgreSQL; these tables preserve the
-- reviewed schema inventory without enabling a local mailbox for remote DBs.
CREATE TABLE IF NOT EXISTS password_reset_tokens (
    token_hash TEXT PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id),
    password_version TEXT NOT NULL,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS password_reset_owner ON password_reset_tokens(user_id);
CREATE TABLE IF NOT EXISTS password_reset_limits (
    bucket TEXT PRIMARY KEY,
    attempts BIGINT NOT NULL CHECK(attempts > 0),
    window_started_at TEXT NOT NULL
);

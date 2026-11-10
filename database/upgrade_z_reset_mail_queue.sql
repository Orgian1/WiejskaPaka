-- Explicit schema provisioning for a NEW disposable PostgreSQL test database.
-- Declares storage only; no worker, HTTP route or delivery is enabled.

CREATE TABLE IF NOT EXISTS reset_mail_queue (
 id TEXT PRIMARY KEY,
 user_id BIGINT NOT NULL REFERENCES users(id),
 token_hash TEXT NOT NULL UNIQUE,
 event TEXT NOT NULL CHECK(event='password_reset'),
 key_id TEXT NOT NULL,
 payload BYTEA,
 created_at BIGINT NOT NULL,
 expires_at BIGINT NOT NULL,
 state TEXT NOT NULL CHECK(state IN ('queued','leased','accepted','uncertain','failed','expired')),
 attempts INTEGER NOT NULL DEFAULT 0 CHECK(attempts BETWEEN 0 AND 3),
 available_at BIGINT NOT NULL,
 owner TEXT,
 lease_until BIGINT,
 started_at BIGINT,
 result TEXT,
 CHECK(expires_at>created_at),
 CHECK((state IN ('queued','leased') AND payload IS NOT NULL) OR
       (state IN ('accepted','uncertain','failed','expired') AND payload IS NULL)),
 CHECK((state='leased' AND owner IS NOT NULL AND lease_until IS NOT NULL) OR
       (state!='leased' AND owner IS NULL AND lease_until IS NULL AND started_at IS NULL))
);
CREATE INDEX IF NOT EXISTS reset_mail_ready ON reset_mail_queue(state,available_at,created_at);

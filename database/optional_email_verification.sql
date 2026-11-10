-- Opt-in verification registry, budgets and encrypted outbox. Apply manually.
BEGIN;

CREATE TABLE account_email_proofs (
 user_id BIGINT PRIMARY KEY REFERENCES users(id),
 email_hash TEXT NOT NULL,
 token_hash TEXT,
 issued_at BIGINT NOT NULL,
 expires_at BIGINT NOT NULL,
 verified_at BIGINT
);

CREATE TABLE email_verification_limits (
 bucket TEXT PRIMARY KEY, attempts BIGINT NOT NULL, window_started BIGINT NOT NULL
);
CREATE TABLE email_verification_queue (
 id TEXT PRIMARY KEY,
 user_id BIGINT NOT NULL UNIQUE REFERENCES users(id),
 event TEXT NOT NULL CHECK(event='email_verification'),
 token_hash TEXT NOT NULL,
 key_id TEXT NOT NULL,
 payload BYTEA,
 created_at BIGINT NOT NULL,
 expires_at BIGINT NOT NULL,
 state TEXT NOT NULL CHECK(state IN ('queued','started','accepted','uncertain','failed','expired')),
 started_at BIGINT
);

COMMIT;

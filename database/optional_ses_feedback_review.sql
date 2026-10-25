-- Private encrypted SNS REVIEW archive. Explicit migration only; no listener activation.
BEGIN;
CREATE TABLE ses_feedback_review (
 event_key TEXT PRIMARY KEY REFERENCES ses_feedback_events(event_key),
 raw_hash TEXT NOT NULL,
 key_id TEXT NOT NULL,
 received_at BIGINT NOT NULL,
 expires_at BIGINT NOT NULL CHECK(expires_at>received_at),
 payload BYTEA NOT NULL
);
CREATE INDEX ses_feedback_review_expiry ON ses_feedback_review(expires_at);
COMMIT;

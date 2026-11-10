-- Private authenticated SES feedback journal; no HTTP listener activation.
BEGIN;

CREATE TABLE ses_feedback_events (
 event_key TEXT PRIMARY KEY,
 payload_hash TEXT NOT NULL,
 result TEXT NOT NULL CHECK(result IN ('APPLIED','IGNORED','REVIEW')),
 received_at BIGINT NOT NULL
);

COMMIT;

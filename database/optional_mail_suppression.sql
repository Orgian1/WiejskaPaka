-- Trusted internal suppression registry, no public notification ingestion.
BEGIN;

CREATE TABLE mail_recipient_blocks (
 recipient_hash TEXT PRIMARY KEY,
 reason TEXT NOT NULL CHECK(reason IN ('permanent_bounce','complaint')),
 created_at BIGINT NOT NULL
);

COMMIT;

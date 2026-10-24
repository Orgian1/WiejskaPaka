-- Preparation only. No HTTP or automatic worker activates this outbox.
BEGIN;
CREATE TABLE order_mail_outbox (
 id TEXT PRIMARY KEY,
 buyer_id BIGINT NOT NULL REFERENCES users(id),
 request_key TEXT NOT NULL,
 recipient_hash TEXT NOT NULL CHECK(length(recipient_hash)=64),
 state TEXT NOT NULL CHECK(state IN ('queued','started','accepted','uncertain','failed','skipped')),
 created_at BIGINT NOT NULL,
 started_at BIGINT,
 result TEXT,
 UNIQUE(buyer_id,request_key),
 FOREIGN KEY(buyer_id,request_key) REFERENCES checkout_idempotency(buyer_id,request_key)
);
CREATE INDEX order_mail_ready ON order_mail_outbox(state,created_at,id);
COMMIT;

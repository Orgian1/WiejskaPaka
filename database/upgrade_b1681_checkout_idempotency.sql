-- Apply manually to PostgreSQL test database before enabling Idempotency-Key.
-- Do not apply to Neon without explicit authorization.
CREATE TABLE IF NOT EXISTS checkout_idempotency (
  buyer_id BIGINT NOT NULL REFERENCES users(id),
  request_key TEXT NOT NULL CHECK (length(request_key) BETWEEN 12 AND 100),
  payload_hash TEXT NOT NULL,
  response_json TEXT NOT NULL,
  created_at TEXT NOT NULL,
  PRIMARY KEY (buyer_id, request_key)
);

-- Apply after upgrade_b1681_checkout_idempotency.sql and shipment migrations.
-- Test PostgreSQL only; no production/Neon connection is implied.
-- A direct-order namespace adds seven characters to the 100-character public key.
ALTER TABLE checkout_idempotency DROP CONSTRAINT IF EXISTS checkout_idempotency_request_key_check;
ALTER TABLE checkout_idempotency ADD CONSTRAINT checkout_idempotency_request_key_check
    CHECK (length(request_key) BETWEEN 12 AND 107);

CREATE TABLE IF NOT EXISTS checkout_pin_links (
    order_id BIGINT PRIMARY KEY REFERENCES orders(id),
    buyer_id BIGINT NOT NULL,
    request_key TEXT NOT NULL,
    FOREIGN KEY(buyer_id,request_key) REFERENCES checkout_idempotency(buyer_id,request_key)
);
CREATE INDEX IF NOT EXISTS checkout_pin_links_request ON checkout_pin_links(buyer_id,request_key);
CREATE TABLE IF NOT EXISTS checkout_pin_access (
    buyer_id BIGINT PRIMARY KEY REFERENCES users(id),
    attempts BIGINT NOT NULL CHECK(attempts BETWEEN 1 AND 5),
    window_started_at TEXT NOT NULL
);

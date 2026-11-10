-- Apply once before starting this version with a PostgreSQL application role.
-- Existing orders are intentionally NOT given retrospective expiry deadlines.
BEGIN;
CREATE TABLE IF NOT EXISTS inventory_reservations (
    order_id BIGINT PRIMARY KEY REFERENCES orders(id),
    expires_at TEXT NOT NULL,
    released_at TEXT
);
CREATE INDEX IF NOT EXISTS inventory_reservations_expiry
    ON inventory_reservations(expires_at) WHERE released_at IS NULL;
COMMIT;

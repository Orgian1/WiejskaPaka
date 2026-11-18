-- WiejskaPaka seller ratings: PostgreSQL migration.
-- Apply only after reviewing with the existing PostgreSQL RLS policy framework.
-- No financial tables or payment balances are changed.
BEGIN;
CREATE TABLE IF NOT EXISTS seller_ratings (
  order_id BIGINT PRIMARY KEY REFERENCES orders(id),
  buyer_id BIGINT NOT NULL REFERENCES users(id),
  seller_id BIGINT NOT NULL REFERENCES users(id),
  stars INTEGER NOT NULL CHECK (stars BETWEEN 1 AND 5),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS seller_ratings_seller_idx ON seller_ratings(seller_id);
-- The application authorizes ratings against the order's buyer and final status.
-- Deny direct table access to PUBLIC; application-specific RLS policies are
-- required before granting access to any non-owner database role.
REVOKE ALL ON TABLE seller_ratings FROM PUBLIC;
ALTER TABLE seller_ratings ENABLE ROW LEVEL SECURITY;
ALTER TABLE seller_ratings FORCE ROW LEVEL SECURITY;
COMMIT;

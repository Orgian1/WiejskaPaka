-- WiejskaPaka seller ratings: PostgreSQL migration.
-- Requires review against the deployed database role and existing RLS policies.
-- Not a production rollout or an automatic migration.
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
-- The public API exposes only aggregates. Backend database access needs SELECT
-- for summary and buyer's prior rating; the HTTP layer never exposes raw rows.
REVOKE ALL ON TABLE seller_ratings FROM PUBLIC;
ALTER TABLE seller_ratings ENABLE ROW LEVEL SECURITY;
ALTER TABLE seller_ratings FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS seller_ratings_read ON seller_ratings;
CREATE POLICY seller_ratings_read ON seller_ratings
  FOR SELECT USING (true);
DROP POLICY IF EXISTS seller_ratings_buyer_insert ON seller_ratings;
CREATE POLICY seller_ratings_buyer_insert ON seller_ratings
  FOR INSERT WITH CHECK (
    buyer_id = NULLIF(current_setting('wiejskapaka.actor_id', true), '')::BIGINT
    AND EXISTS (
      SELECT 1 FROM orders o
      WHERE o.id = order_id AND o.buyer_id = buyer_id
        AND o.farmer_id = seller_id AND o.status = 'odebrane'
    )
  );
-- No UPDATE or DELETE policies: submitted reviews are immutable.
-- Grants to the actual application DB role must be checked during deployment.
-- The table owner is also subject to these policies because FORCE RLS is set.
COMMIT;

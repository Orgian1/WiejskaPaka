-- Ratings storage for the application schema. Apply before the RLS gateway.
BEGIN;
CREATE TABLE IF NOT EXISTS seller_ratings (
  order_id BIGINT PRIMARY KEY REFERENCES orders(id),
  buyer_id BIGINT NOT NULL REFERENCES users(id),
  seller_id BIGINT NOT NULL REFERENCES users(id),
  stars INTEGER NOT NULL CHECK (stars BETWEEN 1 AND 5),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS seller_ratings_seller_idx ON seller_ratings(seller_id);
REVOKE ALL ON TABLE seller_ratings FROM PUBLIC;
COMMIT;

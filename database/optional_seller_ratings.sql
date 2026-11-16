-- Seller ratings; immutable purchase evidence is not changed.

CREATE TABLE IF NOT EXISTS seller_ratings (
 order_id BIGINT PRIMARY KEY REFERENCES orders(id),
 buyer_id BIGINT NOT NULL REFERENCES users(id),
 farmer_id BIGINT NOT NULL REFERENCES users(id),
 stars INTEGER NOT NULL CHECK(stars BETWEEN 1 AND 5),
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS seller_ratings_farmer ON seller_ratings(farmer_id);

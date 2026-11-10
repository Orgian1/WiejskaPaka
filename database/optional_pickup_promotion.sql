-- Seller campaign entitlement only. No wallet entries or charges.
BEGIN;
CREATE TABLE IF NOT EXISTS pickup_promotion_grants (
 farmer_id BIGINT NOT NULL REFERENCES users(id), campaign TEXT NOT NULL,
 redeemed_at BIGINT NOT NULL, expires_at BIGINT NOT NULL,
 point_limit BIGINT NOT NULL CHECK(point_limit=3),
 PRIMARY KEY(farmer_id,campaign), CHECK(redeemed_at<expires_at)
);
COMMIT;

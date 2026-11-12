-- Three-point entitlements, no charging or payment transport.
BEGIN;

CREATE TABLE pickup_promo_codes (
 code TEXT PRIMARY KEY,
 expires_on TEXT NOT NULL,
 max_redemptions INTEGER NOT NULL CHECK(max_redemptions BETWEEN 1 AND 1000000),
 redemption_count INTEGER NOT NULL DEFAULT 0 CHECK(redemption_count>=0 AND redemption_count<=max_redemptions),
 active INTEGER NOT NULL CHECK(active IN (0,1))
);
CREATE TABLE pickup_promo_grants (
 id TEXT PRIMARY KEY,
 user_id BIGINT NOT NULL REFERENCES users(id),
 code TEXT NOT NULL REFERENCES pickup_promo_codes(code),
 expires_on TEXT NOT NULL,
 remaining INTEGER NOT NULL CHECK(remaining BETWEEN 0 AND 3),
 UNIQUE(user_id,code)
);
CREATE TABLE pickup_promo_points (
 point_id BIGINT PRIMARY KEY REFERENCES pickup_points(id),
 grant_id TEXT NOT NULL REFERENCES pickup_promo_grants(id)
);
CREATE INDEX pickup_promo_grants_user_idx ON pickup_promo_grants(user_id,expires_on);
COMMIT;

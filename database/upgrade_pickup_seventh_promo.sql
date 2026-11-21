-- Keep existing codes and grants in the three-point promotion.
BEGIN;
ALTER TABLE pickup_promo_codes ADD COLUMN IF NOT EXISTS kind TEXT NOT NULL DEFAULT 'starter'
    CHECK (kind IN ('starter', 'seventh'));
ALTER TABLE pickup_promo_grants ADD COLUMN IF NOT EXISTS kind TEXT NOT NULL DEFAULT 'starter'
    CHECK (kind IN ('starter', 'seventh'));
CREATE UNIQUE INDEX IF NOT EXISTS pickup_promo_seventh_once_per_seller
    ON pickup_promo_grants(user_id) WHERE kind='seventh';
COMMIT;

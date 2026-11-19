-- PostgreSQL: apply after backup; existing promotions retain their previous expiry.
BEGIN;
ALTER TABLE pickup_promo_points ADD COLUMN IF NOT EXISTS free_until TEXT;
COMMIT;

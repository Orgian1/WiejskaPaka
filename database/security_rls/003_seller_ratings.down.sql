-- Stop API/workers, export ratings first. Removes ratings only; not orders/money.
BEGIN;
DO $$ BEGIN
 IF EXISTS(SELECT 1 FROM pg_policy WHERE polrelid=to_regclass('public.seller_ratings') AND polname NOT IN ('wp_guard','wp_read','wp_insert','wp_update','wp_delete')) THEN RAISE EXCEPTION 'Unknown ratings policy requires review'; END IF;
 IF to_regnamespace('wp_rls') IS NOT NULL THEN
  DELETE FROM wp_rls.previous_rls WHERE table_oid=to_regclass('public.seller_ratings');
  DROP FUNCTION IF EXISTS wp_rls.seller_rating_summary(bigint);
 END IF;
END $$;
DROP TABLE IF EXISTS public.seller_ratings;
COMMIT;

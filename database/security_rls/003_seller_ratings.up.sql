-- Manual upgrade, only after compatibility tests on a disposable clone.
BEGIN;
DO $$ BEGIN
 IF current_setting('wp_rls.api_compatibility_verified',true) IS DISTINCT FROM 'yes'
 AND (current_setting('wp_rls.disposable_test',true)='yes' AND current_database() ~ '^wp_test_') IS DISTINCT FROM true
 THEN RAISE EXCEPTION 'Seller ratings compatibility verification required'; END IF;
END $$;
CREATE TABLE IF NOT EXISTS public.seller_ratings (
 order_id BIGINT PRIMARY KEY REFERENCES public.orders(id),
 buyer_id BIGINT NOT NULL REFERENCES public.users(id),
 farmer_id BIGINT NOT NULL REFERENCES public.users(id),
 stars INTEGER NOT NULL CHECK(stars BETWEEN 1 AND 5),
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS seller_ratings_farmer ON public.seller_ratings(farmer_id);
DO $upgrade$ DECLARE n text; BEGIN
 IF to_regnamespace('wp_rls') IS NOT NULL THEN
  IF EXISTS(SELECT 1 FROM pg_policy WHERE polrelid='public.seller_ratings'::regclass AND polname NOT IN ('wp_guard','wp_read','wp_insert','wp_update','wp_delete')) THEN RAISE EXCEPTION 'Unknown ratings policy requires review'; END IF;
  INSERT INTO wp_rls.previous_rls SELECT oid,relrowsecurity,relforcerowsecurity FROM pg_class WHERE oid='public.seller_ratings'::regclass ON CONFLICT(table_oid) DO NOTHING;
  FOREACH n IN ARRAY ARRAY['wp_guard','wp_read','wp_insert','wp_update','wp_delete'] LOOP
   EXECUTE format('DROP POLICY IF EXISTS %I ON public.seller_ratings',n);
  END LOOP;
  ALTER TABLE public.seller_ratings ENABLE ROW LEVEL SECURITY;
  ALTER TABLE public.seller_ratings FORCE ROW LEVEL SECURITY;
  GRANT SELECT,INSERT ON public.seller_ratings TO wp_rls_executor;
  REVOKE UPDATE,DELETE ON public.seller_ratings FROM wp_rls_executor;
  GRANT SELECT ON public.seller_ratings TO wp_rls_guard,wp_rls_backup;
  CREATE POLICY wp_guard ON public.seller_ratings FOR SELECT TO wp_rls_guard,wp_rls_backup USING(true);
  CREATE POLICY wp_read ON public.seller_ratings FOR SELECT TO wp_rls_executor
   USING(wp_rls.allowed('sessions',jsonb_build_object('user_id',buyer_id),'select'));
  CREATE POLICY wp_insert ON public.seller_ratings FOR INSERT TO wp_rls_executor WITH CHECK (
   wp_rls.allowed('sessions',jsonb_build_object('user_id',buyer_id),'insert')
   AND EXISTS(SELECT 1 FROM public.users u WHERE u.id=seller_ratings.buyer_id AND u.role='klient')
   AND EXISTS(SELECT 1 FROM public.orders o WHERE o.id=seller_ratings.order_id AND o.buyer_id=seller_ratings.buyer_id AND o.farmer_id=seller_ratings.farmer_id AND o.status='odebrane' AND o.pin_used=1 AND o.confirmed_at IS NOT NULL));
  CREATE POLICY wp_update ON public.seller_ratings FOR UPDATE TO wp_rls_executor USING(false) WITH CHECK(false);
  CREATE POLICY wp_delete ON public.seller_ratings FOR DELETE TO wp_rls_executor USING(false);
  EXECUTE $function$CREATE OR REPLACE FUNCTION wp_rls.seller_rating_summary(seller_id bigint)
   RETURNS TABLE(count bigint,total bigint) LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog AS $$
    SELECT count(*),COALESCE(sum(r.stars),0)::bigint FROM public.seller_ratings r WHERE r.farmer_id=seller_id
   $$$function$;
  ALTER FUNCTION wp_rls.seller_rating_summary(bigint) OWNER TO wp_rls_guard;
  REVOKE ALL ON FUNCTION wp_rls.seller_rating_summary(bigint) FROM PUBLIC;
  GRANT EXECUTE ON FUNCTION wp_rls.seller_rating_summary(bigint) TO wp_rls_executor;
 END IF;
END $upgrade$;
COMMIT;

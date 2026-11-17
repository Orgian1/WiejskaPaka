-- Additional manual upgrade for audience-targeted wallet ads.
-- Apply only after 001, 002 and 003 on a tested clone; do not modify production.
BEGIN;
DO $$ BEGIN
 IF current_setting('wp_rls.api_compatibility_verified',true) IS DISTINCT FROM 'yes'
 AND (current_setting('wp_rls.disposable_test',true)='yes' AND current_database() ~ '^wp_test_') IS DISTINCT FROM true
 THEN RAISE EXCEPTION 'Wallet ads audience compatibility verification required'; END IF;
 IF to_regclass('public.wallet_ads') IS NULL THEN
  RAISE EXCEPTION 'Expected wallet_ads from migration 002';
 END IF;
 IF NOT (SELECT c.relrowsecurity AND c.relforcerowsecurity FROM pg_class c WHERE c.oid='public.wallet_ads'::regclass) THEN
  RAISE EXCEPTION 'wallet_ads FORCE RLS must be enabled';
 END IF;
 IF (SELECT COUNT(*) FROM pg_policy WHERE polrelid='public.wallet_ads'::regclass) <> 5
 OR EXISTS (SELECT 1 FROM pg_policy WHERE polrelid='public.wallet_ads'::regclass AND polname NOT IN ('wp_guard','wp_read','wp_insert','wp_update','wp_delete')) THEN
  RAISE EXCEPTION 'Unexpected wallet ads RLS policy configuration';
 END IF;
END $$;
ALTER TABLE public.wallet_ads ADD COLUMN IF NOT EXISTS audience TEXT NOT NULL DEFAULT 'both';
DO $$ BEGIN
 IF EXISTS (SELECT 1 FROM public.wallet_ads WHERE audience NOT IN ('klient','rolnik','both') OR audience IS NULL) THEN
  RAISE EXCEPTION 'Invalid wallet ad audience values';
 END IF;
END $$;
ALTER TABLE public.wallet_ads DROP CONSTRAINT IF EXISTS wallet_ads_audience_check;
ALTER TABLE public.wallet_ads ADD CONSTRAINT wallet_ads_audience_check CHECK (audience IN ('klient','rolnik','both'));
COMMIT;

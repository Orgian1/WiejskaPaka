-- Reverse audience targeting without deleting campaigns, impressions or finance data.
-- Run on isolated clone only after testing rollback of application feature.
BEGIN;
DO $$ BEGIN
 IF current_setting('wp_rls.api_compatibility_verified',true) IS DISTINCT FROM 'yes'
 AND (current_setting('wp_rls.disposable_test',true)='yes' AND current_database() ~ '^wp_test_') IS DISTINCT FROM true
 THEN RAISE EXCEPTION 'Wallet ads audience rollback verification required'; END IF;
 IF to_regclass('public.wallet_ads') IS NULL THEN
  RAISE EXCEPTION 'Expected wallet_ads';
 END IF;
END $$;
UPDATE public.wallet_ads SET audience='both' WHERE audience <> 'both';
-- Keep the column for a safe backward-compatible rollback. Older application
-- versions ignore it; dropping it risks data loss and a table rewrite.
COMMIT;

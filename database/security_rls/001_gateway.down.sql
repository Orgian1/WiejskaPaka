-- Stop API/workers and close pools first. Restore pre-migration login ACL from
-- the deployment inventory, never substitute an owner/superuser login.
BEGIN;
DO $$ DECLARE t record; n text; BEGIN
 FOR t IN SELECT p.*,c.relname FROM wp_rls.previous_rls p JOIN pg_class c ON c.oid=p.table_oid LOOP
  IF EXISTS(SELECT 1 FROM pg_policy WHERE polrelid=t.table_oid AND polname NOT IN ('wp_guard','wp_read','wp_insert','wp_update','wp_delete')) THEN RAISE EXCEPTION 'New policy requires rollback review'; END IF;
  FOREACH n IN ARRAY ARRAY['wp_guard','wp_read','wp_insert','wp_update','wp_delete'] LOOP
   EXECUTE format('DROP POLICY %I ON public.%I',n,t.relname);
  END LOOP;
  IF NOT t.enabled THEN EXECUTE format('ALTER TABLE public.%I DISABLE ROW LEVEL SECURITY',t.relname); END IF;
  IF NOT t.forced THEN EXECUTE format('ALTER TABLE public.%I NO FORCE ROW LEVEL SECURITY',t.relname); END IF;
 END LOOP;
END $$;
REVOKE ALL ON ALL TABLES IN SCHEMA public FROM wp_rls_guard,wp_rls_executor,wp_rls_backup;
REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM wp_rls_executor,wp_rls_backup;
DROP SCHEMA wp_rls CASCADE;
DROP SCHEMA wp_rls_keys CASCADE;
REVOKE USAGE ON SCHEMA public FROM wp_rls_runtime,wp_rls_guard,wp_rls_executor,wp_rls_backup;
-- Shared NOLOGIN roles are intentionally retained: other reviewed databases
-- may depend on them. Remove memberships/roles only from a cluster-wide audit.
COMMIT;

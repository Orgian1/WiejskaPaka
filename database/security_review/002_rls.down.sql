-- Apply before 001_roles.down.sql. Restores flags captured by UP.
BEGIN;
DROP POLICY wp_auth_sessions ON public.sessions;
DROP POLICY wp_auth_users ON public.users;
DO $$ DECLARE t record; BEGIN
 FOR t IN SELECT p.*,c.relname FROM wp_security.previous_rls p JOIN pg_class c ON c.oid=p.table_oid LOOP
  EXECUTE format('DROP POLICY wp_select ON public.%I',t.relname);
  EXECUTE format('DROP POLICY wp_insert ON public.%I',t.relname);
  EXECUTE format('DROP POLICY wp_update ON public.%I',t.relname);
  EXECUTE format('DROP POLICY wp_delete ON public.%I',t.relname);
  IF NOT t.enabled THEN EXECUTE format('ALTER TABLE public.%I DISABLE ROW LEVEL SECURITY',t.relname); END IF;
  IF NOT t.forced THEN EXECUTE format('ALTER TABLE public.%I NO FORCE ROW LEVEL SECURITY',t.relname); END IF;
 END LOOP;
END $$;
REVOKE SELECT (id,role,email) ON public.users FROM wp_runtime;
REVOKE SELECT (id,buyer_id,farmer_id,product_id,quantity,subtotal_grosze,delivery_grosze,total_grosze,fulfillment,status,pickup_code,pin_used,created_at,confirmed_at) ON public.orders FROM wp_runtime;
REVOKE SELECT ON public.order_locations, public.delivery_assignments FROM wp_runtime;
DROP TABLE wp_security.previous_rls;
COMMIT;

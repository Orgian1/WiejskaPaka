-- REVIEW ONLY. No automatic migration runner includes this directory.
-- Known incompatible with legacy SELECT * and direct financial writes.
BEGIN;
DO $$ BEGIN IF current_setting('wp_security.compatibility_verified', true) IS DISTINCT FROM 'yes' THEN RAISE EXCEPTION 'RLS blocked: API/login/jobs compatibility not verified'; END IF; END $$;
CREATE TABLE wp_security.previous_rls (table_oid oid PRIMARY KEY, enabled boolean NOT NULL, forced boolean NOT NULL);
REVOKE ALL ON wp_security.previous_rls FROM PUBLIC;
DO $migration$
DECLARE t record; predicate text;
BEGIN
 FOR t IN SELECT c.oid, c.relname, c.relrowsecurity, c.relforcerowsecurity FROM pg_class c
 JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' AND c.relkind='r'
 AND c.relname NOT IN ('products','pickup_points','farmer_profiles','pickup_point_coordinates','product_search_names','schema_migrations')
 LOOP
  -- Do not combine with unknown permissive policies or overwrite their state.
  IF EXISTS (SELECT 1 FROM pg_policy WHERE polrelid=t.oid) THEN
    RAISE EXCEPTION 'Existing policy requires manual review: %', t.relname;
  END IF;
  INSERT INTO wp_security.previous_rls VALUES(t.oid,t.relrowsecurity,t.relforcerowsecurity);
  predicate := 'false';
  IF t.relname='users' THEN predicate := 'id=wp_security.actor_id()'; END IF;
  IF t.relname='sessions' THEN predicate := 'false'; END IF;
  IF t.relname='orders' THEN predicate := '(buyer_id=wp_security.actor_id() OR farmer_id=wp_security.actor_id() OR wp_security.actor_role()=''admin'' OR (fulfillment=''dostawa'' AND status=''w_drodze_testowo'' AND pin_used=0 AND confirmed_at IS NULL AND EXISTS (SELECT 1 FROM public.delivery_assignments d WHERE d.order_id=orders.id AND d.courier_id=wp_security.actor_id())))'; END IF;
  IF t.relname='delivery_assignments' THEN predicate := 'courier_id=wp_security.actor_id() OR assigned_by=wp_security.actor_id()'; END IF;
  IF t.relname='order_locations' THEN predicate := 'EXISTS (SELECT 1 FROM public.orders o WHERE o.id=order_locations.order_id AND (o.buyer_id=wp_security.actor_id() OR (o.farmer_id=wp_security.actor_id() AND o.fulfillment=''odbior'') OR (o.fulfillment=''dostawa'' AND o.status=''w_drodze_testowo'' AND o.pin_used=0 AND o.confirmed_at IS NULL AND EXISTS (SELECT 1 FROM public.delivery_assignments d WHERE d.order_id=o.id AND d.courier_id=wp_security.actor_id()))))'; END IF;
  IF t.relname='shipment_groups' THEN predicate := 'buyer_id=wp_security.actor_id() OR farmer_id=wp_security.actor_id() OR wp_security.actor_role()=''admin'''; END IF;
  IF t.relname='shipment_order_links' THEN predicate := 'EXISTS (SELECT 1 FROM public.shipment_groups s WHERE s.id=shipment_order_links.shipment_id)'; END IF;
  IF t.relname='order_purchase_records' THEN predicate := 'buyer_id=wp_security.actor_id() OR farmer_id=wp_security.actor_id()'; END IF;
  IF t.relname='saved_cart_items' THEN predicate := 'buyer_id=wp_security.actor_id()'; END IF;
  IF t.relname='notifications' THEN predicate := 'user_id=wp_security.actor_id()'; END IF;
  IF t.relname='seller_compliance' THEN predicate := 'farmer_id=wp_security.actor_id() OR wp_security.actor_role()=''admin'''; END IF;
  IF t.relname='wallet_preview_accounts' AND EXISTS (SELECT 1 FROM pg_attribute WHERE attrelid=t.oid AND attname='user_id' AND NOT attisdropped) THEN predicate := 'user_id=wp_security.actor_id()'; END IF;
  IF t.relname='wallet_preview_entries' AND EXISTS (SELECT 1 FROM pg_attribute WHERE attrelid=t.oid AND attname='user_id' AND NOT attisdropped) THEN predicate := 'user_id=wp_security.actor_id()'; END IF;
  IF t.relname='wallet_preview_terms' AND EXISTS (SELECT 1 FROM pg_attribute WHERE attrelid=t.oid AND attname='user_id' AND NOT attisdropped) THEN predicate := 'user_id=wp_security.actor_id()'; END IF;
  IF t.relname='wallet_preview_resolutions' AND EXISTS (SELECT 1 FROM pg_attribute WHERE attrelid=t.oid AND attname='user_id' AND NOT attisdropped) THEN predicate := 'user_id=wp_security.actor_id()'; END IF;
  IF t.relname='wallet_preview_operation_fences' AND EXISTS (SELECT 1 FROM pg_attribute WHERE attrelid=t.oid AND attname='user_id' AND NOT attisdropped) THEN predicate := 'user_id=wp_security.actor_id()'; END IF;
  IF t.relname='wallet_preview_withdrawals' AND EXISTS (SELECT 1 FROM pg_attribute WHERE attrelid=t.oid AND attname='user_id' AND NOT attisdropped) THEN predicate := 'user_id=wp_security.actor_id()'; END IF;
  IF t.relname='commission_drafts' AND EXISTS (SELECT 1 FROM pg_attribute WHERE attrelid=t.oid AND attname='farmer_id' AND NOT attisdropped) THEN predicate := 'farmer_id=wp_security.actor_id() OR wp_security.actor_role()=''admin'''; END IF;
  IF t.relname='invoice_drafts' AND EXISTS (SELECT 1 FROM pg_attribute WHERE attrelid=t.oid AND attname='farmer_id' AND NOT attisdropped) THEN predicate := 'farmer_id=wp_security.actor_id() OR wp_security.actor_role()=''admin'''; END IF;
  IF t.relname='payout_plan_batches' AND EXISTS (SELECT 1 FROM pg_attribute WHERE attrelid=t.oid AND attname='farmer_id' AND NOT attisdropped) THEN predicate := 'farmer_id=wp_security.actor_id() OR wp_security.actor_role()=''admin'''; END IF;
  IF t.relname='payout_reservations' AND EXISTS (SELECT 1 FROM pg_attribute WHERE attrelid=t.oid AND attname='farmer_id' AND NOT attisdropped) THEN predicate := 'farmer_id=wp_security.actor_id() OR wp_security.actor_role()=''admin'''; END IF;
  EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY',t.relname);
  EXECUTE format('ALTER TABLE public.%I FORCE ROW LEVEL SECURITY',t.relname);
  EXECUTE format('CREATE POLICY wp_select ON public.%I FOR SELECT TO wp_runtime USING (%s)',t.relname,predicate);
  EXECUTE format('CREATE POLICY wp_insert ON public.%I FOR INSERT TO wp_runtime WITH CHECK (false)',t.relname);
  EXECUTE format('CREATE POLICY wp_update ON public.%I FOR UPDATE TO wp_runtime USING (false) WITH CHECK (false)',t.relname);
  EXECUTE format('CREATE POLICY wp_delete ON public.%I FOR DELETE TO wp_runtime USING (false)',t.relname);
 END LOOP;
END $migration$;
-- Authentication is possible before actor context. Definer has only SELECT on
-- these two tables, no login, no membership and no BYPASSRLS; no policy cycle.
CREATE POLICY wp_auth_sessions ON public.sessions FOR SELECT TO wp_authenticator USING (true);
CREATE POLICY wp_auth_users ON public.users FOR SELECT TO wp_authenticator USING (true);
-- No GRANT ALL; column grants keep hashes/PINs out of the runtime SQL surface.
GRANT SELECT (id,role,email) ON public.users TO wp_runtime;
GRANT SELECT (id,buyer_id,farmer_id,product_id,quantity,subtotal_grosze,delivery_grosze,total_grosze,fulfillment,status,pickup_code,pin_used,created_at,confirmed_at) ON public.orders TO wp_runtime;
GRANT SELECT ON public.order_locations, public.delivery_assignments TO wp_runtime;
COMMIT;

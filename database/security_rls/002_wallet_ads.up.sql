-- Manual upgrade only. Stop API/workers; confirm API gate before applying.
BEGIN;
DO $$ BEGIN
 IF current_setting('wp_rls.api_compatibility_verified',true) IS DISTINCT FROM 'yes'
 AND (current_setting('wp_rls.disposable_test',true)='yes' AND current_database() ~ '^wp_test_') IS DISTINCT FROM true
 THEN RAISE EXCEPTION 'Wallet ads compatibility verification required'; END IF;
END $$;
-- Wallet ads: no financial tables or balances are modified.

CREATE TABLE IF NOT EXISTS wallet_ads (
 id TEXT PRIMARY KEY, advertiser TEXT NOT NULL, url TEXT NOT NULL,
 image TEXT NOT NULL, starts_at BIGINT NOT NULL, ends_at BIGINT NOT NULL,
 enabled INTEGER NOT NULL CHECK(enabled IN (0,1)), sort_order INTEGER NOT NULL,
 deleted INTEGER NOT NULL DEFAULT 0 CHECK(deleted IN (0,1)), CHECK(ends_at>starts_at)
);
CREATE TABLE IF NOT EXISTS wallet_ad_accounts (
 user_id BIGINT NOT NULL PRIMARY KEY REFERENCES users(id), last_shown BIGINT NOT NULL DEFAULT 0,
 last_ad_id TEXT REFERENCES wallet_ads(id)
);
CREATE TABLE IF NOT EXISTS wallet_ad_impressions (
 id TEXT PRIMARY KEY, user_id BIGINT NOT NULL REFERENCES users(id),
 ad_id TEXT NOT NULL REFERENCES wallet_ads(id), request_key TEXT NOT NULL,
 created_at BIGINT NOT NULL, clicked INTEGER NOT NULL DEFAULT 0 CHECK(clicked IN (0,1)),
 UNIQUE(user_id,request_key)
);
CREATE INDEX IF NOT EXISTS wallet_ad_stats ON wallet_ad_impressions(ad_id);

DO $upgrade$ BEGIN
 IF to_regnamespace('wp_rls') IS NOT NULL THEN
 EXECUTE $definition$CREATE OR REPLACE FUNCTION wp_rls.allowed(t text,r jsonb,op text) RETURNS boolean
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE c wp_rls.context; proof text; p jsonb; owner_id bigint; o public.orders; s public.shipment_groups;
BEGIN
 SELECT * INTO c FROM wp_rls.context WHERE pid=pg_backend_pid() AND xid=txid_current();
 IF NOT FOUND THEN
  -- Read-only diagnostics cannot write a context/nonce table. Their context
  -- is a full signed, transaction-bound proof; naked GUC IDs remain untrusted.
  IF current_setting('transaction_read_only')<>'on' THEN RETURN false; END IF;
  proof:=current_setting('wp_rls.read_proof',true);
  IF wp_rls.verify(proof,current_setting('wp_rls.read_signature',true)) IS DISTINCT FROM true THEN RETURN false; END IF;
  p:=proof::jsonb;
  IF (p->>'pid')::integer IS DISTINCT FROM pg_backend_pid() OR (p->>'xid')::bigint IS DISTINCT FROM txid_current() OR p->>'db' IS DISTINCT FROM current_database() OR (p->>'expires')::bigint<extract(epoch FROM statement_timestamp())::bigint THEN RETURN false; END IF;
  SELECT v.id,v.role INTO c.actor,c.role FROM wp_rls.resolve(p->>'bearer') v;
  c.purpose:=p->>'scope';c.statement:=p->>'sql';
 END IF;
 IF c.purpose='maintenance' THEN RETURN true; END IF;
 IF c.purpose='auth' AND t IN ('users','sessions','login_attempts','password_change_access','password_reset_tokens','password_reset_limits','reset_mail_queue','account_email_proofs','email_verification_queue','email_verification_limits','mail_send_budget','mail_send_attempts','mail_recipient_blocks') THEN RETURN true; END IF;
 IF op='select' AND t IN ('users','products','pickup_points','farmer_profiles','pickup_point_coordinates','pickup_point_dates','product_sale_units','product_search_names','seller_public_logins','seller_delivery_windows','user_photos','schema_migrations') THEN RETURN true; END IF;
 IF c.actor IS NULL THEN RETURN false; END IF;
 IF t='orders' AND op='update' THEN
  SELECT * INTO o FROM public.orders WHERE id=(r->>'id')::bigint;
  IF o.id IS NOT NULL AND ((r->>'buyer_id')::bigint IS DISTINCT FROM o.buyer_id OR (r->>'farmer_id')::bigint IS DISTINCT FROM o.farmer_id) THEN RETURN false; END IF;
 END IF;
 IF t='shipment_groups' AND op='update' THEN
  SELECT * INTO s FROM public.shipment_groups WHERE id=r->>'id';
  IF s.id IS NOT NULL AND ((r->>'buyer_id')::bigint IS DISTINCT FROM s.buyer_id OR (r->>'farmer_id')::bigint IS DISTINCT FROM s.farmer_id) THEN RETURN false; END IF;
 END IF;
 IF t='order_locations' AND c.role<>'admin' THEN
  SELECT * INTO o FROM public.orders WHERE id=(r->>'order_id')::bigint;
  IF o.buyer_id=c.actor THEN RETURN true; END IF;
  IF o.farmer_id=c.actor THEN
   RETURN o.fulfillment='odbior' OR c.statement ~* '^SELECT\s+pickup_point_id\s+FROM\s+order_locations\s+WHERE\s+order_id\s*='
    OR EXISTS(SELECT 1 FROM public.address_delivery_requests a WHERE a.order_id=o.id);
  END IF;
  RETURN o.fulfillment='dostawa' AND o.status='w_drodze_testowo' AND o.pin_used=0 AND o.confirmed_at IS NULL AND EXISTS(SELECT 1 FROM public.delivery_assignments a WHERE a.order_id=o.id AND a.courier_id=c.actor);
 END IF;
 IF t='wallet_ads' THEN RETURN c.role='admin' OR (op='select' AND c.role IN ('klient','rolnik')); END IF;
 IF t IN ('wallet_ad_accounts','wallet_ad_impressions') THEN RETURN c.role='admin' OR (c.role IN ('klient','rolnik') AND (r->>'user_id')::bigint=c.actor); END IF;
 IF c.role='admin' THEN RETURN true; END IF;
 -- Role/ownership checks in handlers are retained. A statement capability is
 -- required even for the exceptions below; the SQL login cannot invoke DML.
 IF op='update' AND c.statement ~* '^SELECT' AND t IN ('products','pickup_points','farmer_profiles','pickup_point_coordinates','pickup_point_dates','product_sale_units','product_search_names','seller_public_logins','seller_delivery_windows','user_photos') THEN RETURN true; END IF;
 IF t='notifications' AND op='insert' THEN RETURN EXISTS(SELECT 1 FROM public.orders v WHERE v.id=(r->>'order_id')::bigint AND c.actor IN (v.buyer_id,v.farmer_id) AND ((r->>'user_id')::bigint IN (v.buyer_id,v.farmer_id) OR EXISTS(SELECT 1 FROM public.delivery_assignments a WHERE a.order_id=v.id AND a.courier_id=(r->>'user_id')::bigint))); END IF;
 IF t='products' AND op='update' AND c.statement ~* '^UPDATE\s+products\s+SET\s+stock\s*=' THEN RETURN true; END IF;
 IF t IN ('login_attempts','password_reset_limits','email_verification_limits') THEN RETURN true; END IF;
 IF t='sessions' THEN RETURN (r->>'user_id')::bigint=c.actor; END IF;
 IF t='users' THEN RETURN (r->>'id')::bigint=c.actor; END IF;
 IF t='support_case_events' THEN RETURN EXISTS(SELECT 1 FROM public.support_cases v WHERE v.id=r->>'case_id' AND c.actor IN (v.buyer_id,v.farmer_id)); END IF;
 IF r ? 'user_id' THEN RETURN (r->>'user_id')::bigint=c.actor; END IF;
 IF r ? 'buyer_id' OR r ? 'farmer_id' OR r ? 'owner_id' THEN
  IF c.actor IN ((r->>'buyer_id')::bigint,(r->>'farmer_id')::bigint,(r->>'owner_id')::bigint) THEN RETURN true; END IF;
  IF t NOT IN ('orders','shipment_groups') THEN RETURN false; END IF;
 END IF;
 IF t='orders' THEN SELECT * INTO o FROM public.orders WHERE id=(r->>'id')::bigint;
 ELSIF r ? 'order_id' THEN SELECT * INTO o FROM public.orders WHERE id=(r->>'order_id')::bigint;
 END IF;
 IF o.id IS NOT NULL THEN RETURN c.actor IN (o.buyer_id,o.farmer_id) OR EXISTS(SELECT 1 FROM public.delivery_assignments d WHERE d.order_id=o.id AND d.courier_id=c.actor); END IF;
 IF t='shipment_groups' THEN SELECT * INTO s FROM public.shipment_groups WHERE id=r->>'id';
 ELSIF r ? 'shipment_id' THEN SELECT * INTO s FROM public.shipment_groups WHERE id=r->>'shipment_id'; END IF;
 IF s.id IS NOT NULL THEN RETURN c.actor IN (s.buyer_id,s.farmer_id) OR EXISTS(SELECT 1 FROM public.shipment_order_links l JOIN public.delivery_assignments d ON d.order_id=l.order_id WHERE l.shipment_id=s.id AND d.courier_id=c.actor); END IF;
 IF r ? 'product_id' THEN RETURN EXISTS(SELECT 1 FROM public.products p WHERE p.id=(r->>'product_id')::bigint AND p.farmer_id=c.actor); END IF;
 IF r ? 'point_id' THEN RETURN EXISTS(SELECT 1 FROM public.pickup_points p WHERE p.id=(r->>'point_id')::bigint AND p.farmer_id=c.actor); END IF;
 IF t='wallet_preview_terms' THEN RETURN EXISTS(SELECT 1 FROM public.wallet_preview_entries e WHERE e.id=r->>'withdrawal_id' AND e.user_id=c.actor); END IF;
 RETURN false;
END $$;$definition$;
 END IF;
END $upgrade$;
DO $upgrade$ BEGIN
 IF to_regnamespace('wp_rls') IS NOT NULL THEN
 GRANT SELECT,INSERT,UPDATE,DELETE ON public.wallet_ads,public.wallet_ad_accounts,public.wallet_ad_impressions TO wp_rls_executor;
 GRANT SELECT ON public.wallet_ads,public.wallet_ad_accounts,public.wallet_ad_impressions TO wp_rls_guard,wp_rls_backup;
 EXECUTE $policies$DO $$ DECLARE t record; BEGIN
 FOR t IN SELECT c.oid,c.relname,c.relrowsecurity,c.relforcerowsecurity FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' AND c.relkind='r' AND c.relname IN ('wallet_ads','wallet_ad_accounts','wallet_ad_impressions') LOOP
  IF EXISTS(SELECT 1 FROM pg_policy WHERE polrelid=t.oid) THEN
   IF EXISTS(SELECT 1 FROM pg_policy WHERE polrelid=t.oid AND polname NOT IN ('wp_guard','wp_read','wp_insert','wp_update','wp_delete')) THEN RAISE EXCEPTION 'Unknown ads policy'; END IF;
   IF NOT t.relrowsecurity OR NOT t.relforcerowsecurity OR (SELECT count(*) FROM pg_policy WHERE polrelid=t.oid)<>5 THEN RAISE EXCEPTION 'Incomplete ads RLS requires review'; END IF;
   CONTINUE;
  END IF;
  INSERT INTO wp_rls.previous_rls VALUES(t.oid,t.relrowsecurity,t.relforcerowsecurity);
  EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY',t.relname);
  EXECUTE format('ALTER TABLE public.%I FORCE ROW LEVEL SECURITY',t.relname);
  EXECUTE format('CREATE POLICY wp_guard ON public.%I FOR SELECT TO wp_rls_guard,wp_rls_backup USING (true)',t.relname);
  EXECUTE format('CREATE POLICY wp_read ON public.%I FOR SELECT TO wp_rls_executor USING (wp_rls.allowed(%L,to_jsonb(%I),''select''))',t.relname,t.relname,t.relname);
  EXECUTE format('CREATE POLICY wp_insert ON public.%I FOR INSERT TO wp_rls_executor WITH CHECK (wp_rls.allowed(%L,to_jsonb(%I),''insert''))',t.relname,t.relname,t.relname);
  EXECUTE format('CREATE POLICY wp_update ON public.%I FOR UPDATE TO wp_rls_executor USING (wp_rls.allowed(%L,to_jsonb(%I),''update'')) WITH CHECK (wp_rls.allowed(%L,to_jsonb(%I),''update''))',t.relname,t.relname,t.relname,t.relname,t.relname);
  EXECUTE format('CREATE POLICY wp_delete ON public.%I FOR DELETE TO wp_rls_executor USING (wp_rls.allowed(%L,to_jsonb(%I),''delete''))',t.relname,t.relname,t.relname);
 END LOOP;
END $$;
$policies$;
 END IF;
END $upgrade$;
COMMIT;

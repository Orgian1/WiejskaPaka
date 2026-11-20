-- Manual deployment only, after the full RLS API gate. No credentials in SQL.
BEGIN;
DO $$ BEGIN
 IF current_setting('wp_rls.api_compatibility_verified',true) IS DISTINCT FROM 'yes'
  AND (current_database() ~ '^wp_test_' AND current_setting('wp_rls.disposable_test',true)='yes') IS DISTINCT FROM true THEN
  RAISE EXCEPTION 'RLS activation blocked: API compatibility approval required';
 END IF;
END $$;
DO $$ DECLARE n text; r record; BEGIN
 FOREACH n IN ARRAY ARRAY['wp_rls_runtime','wp_rls_executor','wp_rls_guard','wp_rls_backup'] LOOP
  SELECT * INTO r FROM pg_roles WHERE rolname=n;
  IF NOT FOUND THEN EXECUTE format('CREATE ROLE %I NOLOGIN NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE NOREPLICATION',n);
  ELSIF r.rolcanlogin OR r.rolsuper OR r.rolbypassrls OR r.rolcreatedb OR r.rolcreaterole OR r.rolreplication THEN
    RAISE EXCEPTION 'Unsafe existing RLS role';
  END IF;
 END LOOP;
 IF EXISTS (SELECT 1 FROM pg_auth_members m JOIN pg_roles private_role ON private_role.oid=m.roleid WHERE private_role.rolname IN ('wp_rls_executor','wp_rls_guard')) THEN
  RAISE EXCEPTION 'Private RLS roles must not have members';
 END IF;
END $$;
CREATE SCHEMA wp_rls;
REVOKE ALL ON SCHEMA wp_rls FROM PUBLIC;
GRANT USAGE ON SCHEMA wp_rls,public TO wp_rls_runtime,wp_rls_executor,wp_rls_guard,wp_rls_backup;
CREATE SCHEMA wp_rls_keys;
REVOKE ALL ON SCHEMA wp_rls_keys FROM PUBLIC;
GRANT USAGE ON SCHEMA wp_rls_keys TO wp_rls_guard;
CREATE TABLE wp_rls_keys.secrets(singleton boolean PRIMARY KEY CHECK(singleton),key bytea NOT NULL CHECK(length(key)=32));
CREATE TABLE wp_rls.context(pid integer,xid bigint,actor bigint,role text,purpose text,statement text,PRIMARY KEY(pid,xid));
CREATE TABLE wp_rls.consumed(pid integer,xid bigint,nonce text,created_at timestamptz NOT NULL DEFAULT now(),PRIMARY KEY(pid,xid,nonce));
CREATE INDEX wp_rls_consumed_created ON wp_rls.consumed(created_at);
CREATE TABLE wp_rls.previous_rls(table_oid oid PRIMARY KEY,enabled boolean,forced boolean);
REVOKE ALL ON ALL TABLES IN SCHEMA wp_rls FROM PUBLIC;
REVOKE ALL ON ALL TABLES IN SCHEMA wp_rls_keys FROM PUBLIC;
GRANT SELECT ON wp_rls_keys.secrets,wp_rls.context TO wp_rls_guard;
GRANT SELECT ON ALL TABLES IN SCHEMA wp_rls TO wp_rls_backup;
GRANT SELECT,INSERT,UPDATE,DELETE ON wp_rls.context,wp_rls.consumed TO wp_rls_executor;

-- Parse in a bound function call, so pg_stat_activity never exposes literal
-- addresses, hashes or encrypted payloads from a rendered PREPARE statement.
-- This function is SECURITY INVOKER: it grants no data access or execution.
CREATE FUNCTION wp_rls.describe(statement text,name text) RETURNS void
LANGUAGE plpgsql SECURITY INVOKER SET search_path=pg_catalog,public,pg_temp AS $$
BEGIN
 IF name !~ '^wp_desc_[a-f0-9]{24}$' OR statement !~* '^\s*(SELECT|WITH|INSERT|UPDATE|DELETE)\s' THEN RAISE EXCEPTION 'Invalid statement description' USING ERRCODE='42501'; END IF;
 EXECUTE format('PREPARE %I AS %s',name,statement);
END $$;

CREATE FUNCTION wp_rls.verify(payload text, signature text) RETURNS boolean
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE k bytea; inner_key bytea; outer_key bytea; expected bytea; actual bytea; diff integer:=0; i integer;
BEGIN
 SELECT key INTO k FROM wp_rls_keys.secrets WHERE singleton;
 IF k IS NULL OR signature IS NULL OR length(signature)<>64 THEN RETURN false; END IF;
 inner_key:=decode(repeat('00',64),'hex');outer_key:=inner_key;
 FOR i IN 0..63 LOOP
  inner_key:=set_byte(inner_key,i,(CASE WHEN i<length(k) THEN get_byte(k,i) ELSE 0 END) # 54);
  outer_key:=set_byte(outer_key,i,(CASE WHEN i<length(k) THEN get_byte(k,i) ELSE 0 END) # 92);
 END LOOP;
 expected:=sha256(outer_key || sha256(inner_key || convert_to(payload,'UTF8')));
 BEGIN actual:=decode(signature,'hex'); EXCEPTION WHEN invalid_parameter_value THEN RETURN false; END;
 FOR i IN 0..31 LOOP diff:=diff | (get_byte(expected,i) # get_byte(actual,i)); END LOOP;
 RETURN diff=0;
END $$;

CREATE FUNCTION wp_rls.allowed(t text,r jsonb,op text) RETURNS boolean
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
 IF op='select' AND t IN ('product_categories','product_subcategories','product_classifications','product_listing_states') THEN RETURN true; END IF;
 IF t='marketplace_ad_campaigns' THEN
  RETURN c.role='admin' OR (op='select' AND (r->>'enabled')::integer=1
   AND (r->>'starts_at')::bigint<=extract(epoch FROM statement_timestamp())
   AND (r->>'ends_at')::bigint>extract(epoch FROM statement_timestamp()));
 END IF;
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
 IF t='seller_ratings' THEN
  IF op='select' THEN RETURN c.role='admin' OR (r->>'buyer_id')::bigint=c.actor; END IF;
  RETURN op='insert' AND c.role='klient' AND (r->>'buyer_id')::bigint=c.actor
   AND EXISTS (SELECT 1 FROM public.orders v WHERE v.id=(r->>'order_id')::bigint
    AND v.buyer_id=c.actor AND v.farmer_id=(r->>'seller_id')::bigint
    AND v.status='odebrane' AND v.pin_used=1 AND v.confirmed_at IS NOT NULL);
 END IF;
 IF t='wallet_ads' THEN
  RETURN c.role='admin' OR (op='select' AND c.role IN ('klient','rolnik')
   AND r->>'audience' IN (c.role,'both') AND (r->>'enabled')::integer=1 AND (r->>'deleted')::integer=0
   AND (r->>'starts_at')::bigint<=extract(epoch FROM statement_timestamp())
   AND (r->>'ends_at')::bigint>extract(epoch FROM statement_timestamp()));
 END IF;
 IF t='shipment_public_refs' AND op='select' THEN
  RETURN c.role='admin' OR EXISTS (SELECT 1 FROM public.shipment_groups v
   WHERE v.id=r->>'shipment_id' AND c.actor IN (v.buyer_id,v.farmer_id));
 END IF;
 IF t='shipment_public_refs' AND op='insert' THEN
  RETURN EXISTS (SELECT 1 FROM public.shipment_groups v WHERE v.id=r->>'shipment_id'
   AND v.buyer_id=c.actor AND v.farmer_id=(r->>'farmer_id')::bigint);
 END IF;
 IF t='pickup_promo_codes' AND c.role='rolnik' THEN
  RETURN op IN ('select','update') AND (c.statement ~* '^SELECT .* FROM pickup_promo_codes WHERE code='
   OR c.statement ~* '^UPDATE pickup_promo_codes SET redemption_count=redemption_count\+1 WHERE code=');
 END IF;
 IF c.role='admin' THEN RETURN true; END IF;
 -- Role/ownership checks in handlers are retained. A statement capability is
 -- required even for the exceptions below; the SQL login cannot invoke DML.
 IF op='update' AND c.statement ~* '^SELECT' AND t IN ('products','pickup_points','farmer_profiles','pickup_point_coordinates','pickup_point_dates','product_sale_units','product_search_names','seller_public_logins','seller_delivery_windows','user_photos') THEN RETURN true; END IF;
 IF t='notifications' AND op='insert' THEN RETURN EXISTS(SELECT 1 FROM public.orders v WHERE v.id=(r->>'order_id')::bigint AND c.actor IN (v.buyer_id,v.farmer_id) AND ((r->>'user_id')::bigint IN (v.buyer_id,v.farmer_id) OR EXISTS(SELECT 1 FROM public.delivery_assignments a WHERE a.order_id=v.id AND a.courier_id=(r->>'user_id')::bigint))); END IF;
 IF t='products' AND op='update' AND c.statement ~* '^UPDATE\s+products\s+SET\s+stock\s*=' THEN RETURN true; END IF;
 IF t IN ('login_attempts','password_reset_limits','email_verification_limits') THEN RETURN true; END IF;
 IF t='sessions' THEN RETURN (r->>'user_id')::bigint=c.actor; END IF;
 IF t='users' THEN RETURN (r->>'id')::bigint=c.actor; END IF;
 IF t='delivery_schedule_proposals' THEN
  RETURN EXISTS (SELECT 1 FROM public.orders v WHERE v.id=(r->>'anchor_order_id')::bigint
   AND c.actor IN (v.buyer_id,v.farmer_id));
 END IF;
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
END $$;

CREATE FUNCTION wp_rls.execute(payload text,signature text) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,public,pg_temp AS $$
DECLARE p jsonb; actor bigint; actor_role text; statement text; cells text; aliases text; result jsonb; affected bigint; token text; readonly boolean;
BEGIN
 IF octet_length(payload)>16777216 OR wp_rls.verify(payload,signature) IS DISTINCT FROM true THEN RAISE EXCEPTION 'Invalid statement capability' USING ERRCODE='42501'; END IF;
 p:=payload::jsonb;
 IF (p->>'pid')::integer IS DISTINCT FROM pg_backend_pid() OR (p->>'xid')::bigint IS DISTINCT FROM txid_current() OR p->>'db' IS DISTINCT FROM current_database()
  OR (p->>'expires')::bigint<extract(epoch FROM clock_timestamp())::bigint OR (p->>'expires')::bigint>extract(epoch FROM clock_timestamp())::bigint+120
  OR p->>'expires' IS NULL OR p->>'nonce' IS NULL OR jsonb_typeof(p->'columns') IS DISTINCT FROM 'array' OR p->>'scope' IS NULL OR p->>'scope' NOT IN ('request','auth','maintenance') THEN RAISE EXCEPTION 'Invalid statement context' USING ERRCODE='42501'; END IF;
 statement:=p->>'sql';
 IF statement !~* '^\s*(SELECT|WITH|INSERT|UPDATE|DELETE)\s' THEN RAISE EXCEPTION 'Statement kind not allowed' USING ERRCODE='42501'; END IF;
 token:=p->>'bearer';
 SELECT v.id,v.role INTO actor,actor_role FROM wp_rls.resolve(token) v;
 -- A login/reset can operate before identity is established. Request contexts
 -- with a missing/expired token receive no private-row access.
 readonly:=current_setting('transaction_read_only')='on';
 IF readonly THEN
  PERFORM set_config('wp_rls.read_proof',payload,true),set_config('wp_rls.read_signature',signature,true);
 ELSE
  BEGIN
   INSERT INTO wp_rls.consumed(pid,xid,nonce) VALUES(pg_backend_pid(),txid_current(),p->>'nonce');
  EXCEPTION WHEN unique_violation THEN RAISE EXCEPTION 'Statement capability already consumed' USING ERRCODE='42501'; END;
  DELETE FROM wp_rls.consumed WHERE created_at<now()-interval '1 hour';
  INSERT INTO wp_rls.context VALUES(pg_backend_pid(),txid_current(),actor,actor_role,p->>'scope',statement);
 END IF;
 IF jsonb_array_length(p->'columns')>0 THEN
  SELECT string_agg(format('c%s',n),',' ORDER BY n),string_agg(format('c%s::text',n),',' ORDER BY n)
   INTO aliases,cells FROM generate_series(0,jsonb_array_length(p->'columns')-1) n;
  EXECUTE format('WITH wp_result(%s) AS (%s) SELECT jsonb_build_object(''rows'',coalesce(jsonb_agg(jsonb_build_array(%s)),''[]''::jsonb),''count'',count(*)) FROM wp_result',aliases,statement,cells) INTO result;
 ELSE
  EXECUTE statement;GET DIAGNOSTICS affected=ROW_COUNT;
  result:=jsonb_build_object('rows','[]'::jsonb,'count',affected);
 END IF;
 IF readonly THEN
  PERFORM set_config('wp_rls.read_proof','',true),set_config('wp_rls.read_signature','',true);
 ELSE
  DELETE FROM wp_rls.context WHERE pid=pg_backend_pid() AND xid=txid_current();
 END IF;
 RETURN result;
END $$;
-- Resolver reads need their own RLS exception, not BYPASSRLS or table ownership.
GRANT SELECT ON ALL TABLES IN SCHEMA public TO wp_rls_guard,wp_rls_backup;
GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA public TO wp_rls_executor;
GRANT USAGE,SELECT ON ALL SEQUENCES IN SCHEMA public TO wp_rls_executor;
GRANT SELECT ON ALL SEQUENCES IN SCHEMA public TO wp_rls_backup;
-- Preserve existing immutable financial snapshots.
REVOKE UPDATE,DELETE ON public.wallet_preview_terms,public.wallet_preview_resolutions,public.wallet_preview_operation_fences,public.seller_ratings FROM wp_rls_executor;
-- Verifier uses direct SELECT of sessions/users before context exists.
GRANT SELECT ON public.sessions,public.users TO wp_rls_executor;
DO $$ DECLARE t record; BEGIN
 FOR t IN SELECT c.oid,c.relname,c.relrowsecurity,c.relforcerowsecurity FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' AND c.relkind='r' LOOP
  IF EXISTS(SELECT 1 FROM pg_policy WHERE polrelid=t.oid) THEN RAISE EXCEPTION 'Existing RLS policies require review: %',t.relname; END IF;
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
-- Session resolution itself is narrowly delegated to the guard, to avoid a
-- session-policy cycle. execute() calls this helper before installing context.
CREATE FUNCTION wp_rls.resolve(token text) RETURNS TABLE(id bigint,role text)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog AS $$
 SELECT u.id,u.role::text FROM public.sessions s JOIN public.users u ON u.id=s.user_id WHERE s.token_hash=encode(sha256(convert_to(token,'UTF8')),'hex') AND s.expires_at::timestamptz>statement_timestamp()
$$;

-- Public endpoints get these projections without access to private rows.
CREATE FUNCTION wp_rls.seller_rating_summary(seller bigint) RETURNS TABLE(count bigint,total bigint)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog AS $$
 SELECT count(*),coalesce(sum(r.stars),0) FROM public.seller_ratings r WHERE r.seller_id=seller
$$;
CREATE FUNCTION wp_rls.pickup_point_entitled(point bigint,moment timestamptz,allow_unrecorded boolean) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog AS $$
 SELECT EXISTS (SELECT 1 FROM public.pickup_point_periods p
  WHERE p.point_id=point AND p.starts_at::timestamptz<=moment AND p.ends_at::timestamptz>moment)
 OR (allow_unrecorded AND NOT EXISTS (SELECT 1 FROM public.pickup_point_periods p WHERE p.point_id=point))
$$;

GRANT CREATE ON SCHEMA wp_rls TO wp_rls_guard,wp_rls_executor;
ALTER FUNCTION wp_rls.verify(text,text) OWNER TO wp_rls_guard;
ALTER FUNCTION wp_rls.allowed(text,jsonb,text) OWNER TO wp_rls_guard;
ALTER FUNCTION wp_rls.resolve(text) OWNER TO wp_rls_guard;
ALTER FUNCTION wp_rls.seller_rating_summary(bigint) OWNER TO wp_rls_guard;
ALTER FUNCTION wp_rls.pickup_point_entitled(bigint,timestamptz,boolean) OWNER TO wp_rls_guard;
ALTER FUNCTION wp_rls.execute(text,text) OWNER TO wp_rls_executor;
REVOKE CREATE ON SCHEMA wp_rls FROM wp_rls_guard,wp_rls_executor;
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA wp_rls FROM PUBLIC;
GRANT EXECUTE ON FUNCTION wp_rls.verify(text,text),wp_rls.allowed(text,jsonb,text),wp_rls.resolve(text),
 wp_rls.seller_rating_summary(bigint),wp_rls.pickup_point_entitled(bigint,timestamptz,boolean) TO wp_rls_executor;
GRANT EXECUTE ON FUNCTION wp_rls.execute(text,text),wp_rls.describe(text,text) TO wp_rls_runtime;
COMMIT;

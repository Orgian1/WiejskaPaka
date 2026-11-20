BEGIN;

CREATE TABLE IF NOT EXISTS public.pickup_point_arrivals (
    point_id BIGINT PRIMARY KEY REFERENCES public.pickup_points(id) ON DELETE CASCADE,
    confirmed_at TEXT NOT NULL
);

-- Fresh fixtures apply the gateway after the schema. Existing secured databases
-- need the same ownership-based policies for this new table.
DO $$
DECLARE target_oid oid := 'public.pickup_point_arrivals'::regclass;
BEGIN
    IF to_regnamespace('wp_rls') IS NULL THEN
        RETURN;
    END IF;
    IF EXISTS (SELECT 1 FROM wp_rls.previous_rls WHERE table_oid=target_oid) THEN
        RETURN;
    END IF;
    INSERT INTO wp_rls.previous_rls
    SELECT oid,relrowsecurity,relforcerowsecurity FROM pg_class WHERE oid=target_oid;
    ALTER TABLE public.pickup_point_arrivals ENABLE ROW LEVEL SECURITY;
    ALTER TABLE public.pickup_point_arrivals FORCE ROW LEVEL SECURITY;
    GRANT SELECT ON public.pickup_point_arrivals TO wp_rls_guard,wp_rls_backup;
    GRANT SELECT,INSERT,UPDATE,DELETE ON public.pickup_point_arrivals TO wp_rls_executor;
    CREATE POLICY wp_guard ON public.pickup_point_arrivals FOR SELECT TO wp_rls_guard,wp_rls_backup USING (true);
    CREATE POLICY wp_read ON public.pickup_point_arrivals FOR SELECT TO wp_rls_executor
        USING (wp_rls.allowed('pickup_point_arrivals',to_jsonb(pickup_point_arrivals),'select'));
    CREATE POLICY wp_insert ON public.pickup_point_arrivals FOR INSERT TO wp_rls_executor
        WITH CHECK (wp_rls.allowed('pickup_point_arrivals',to_jsonb(pickup_point_arrivals),'insert'));
    CREATE POLICY wp_update ON public.pickup_point_arrivals FOR UPDATE TO wp_rls_executor
        USING (wp_rls.allowed('pickup_point_arrivals',to_jsonb(pickup_point_arrivals),'update'))
        WITH CHECK (wp_rls.allowed('pickup_point_arrivals',to_jsonb(pickup_point_arrivals),'update'));
    CREATE POLICY wp_delete ON public.pickup_point_arrivals FOR DELETE TO wp_rls_executor
        USING (wp_rls.allowed('pickup_point_arrivals',to_jsonb(pickup_point_arrivals),'delete'));
END $$;

COMMIT;

CREATE TABLE IF NOT EXISTS incubator_invoice_entries (
 id TEXT PRIMARY KEY,
 mode TEXT NOT NULL CHECK (mode IN ('test','verified')),
 kind TEXT NOT NULL CHECK (kind IN ('withdrawal_fee','pickup_point','advertising','refund')),
 original_id TEXT REFERENCES incubator_invoice_entries(id),
 seller_id BIGINT REFERENCES users(id),
 buyer_name TEXT NOT NULL,
 buyer_address TEXT NOT NULL,
 buyer_nip TEXT,
 service TEXT NOT NULL,
 transaction_id TEXT NOT NULL,
 operator_settlement_id TEXT NOT NULL,
 transaction_on TEXT NOT NULL,
 settled_on TEXT NOT NULL,
 withdrawal_gross_grosze BIGINT,
 amount_grosze BIGINT NOT NULL CHECK (amount_grosze BETWEEN 1 AND 9000000000000),
 refunded_grosze BIGINT NOT NULL DEFAULT 0 CHECK (refunded_grosze BETWEEN 0 AND amount_grosze),
 absorbs_refund INTEGER NOT NULL DEFAULT 0 CHECK (absorbs_refund IN (0,1)),
 recorded_by BIGINT NOT NULL REFERENCES users(id),
 created_at TEXT NOT NULL,
 invoice_number TEXT,
 invoice_number_key TEXT,
 invoice_amount_grosze BIGINT,
 issued_on TEXT,
 issued_by BIGINT REFERENCES users(id),
 UNIQUE (mode, invoice_number_key),
 UNIQUE (mode, transaction_id),
 CHECK ((kind='withdrawal_fee' AND seller_id IS NOT NULL AND withdrawal_gross_grosze IS NOT NULL
         AND withdrawal_gross_grosze BETWEEN 1 AND 9000000000000
         AND amount_grosze=(withdrawal_gross_grosze*500+5000)/10000)
     OR (kind<>'withdrawal_fee' AND withdrawal_gross_grosze IS NULL)),
 CHECK ((kind='refund') = (original_id IS NOT NULL)),
 CHECK (kind='refund' OR absorbs_refund=0),
 CHECK (kind<>'refund' OR refunded_grosze=0),
 CHECK (invoice_number IS NULL OR absorbs_refund=0),
 CHECK ((invoice_number IS NULL AND invoice_number_key IS NULL AND invoice_amount_grosze IS NULL AND issued_on IS NULL AND issued_by IS NULL)
     OR (invoice_number IS NOT NULL AND invoice_number_key IS NOT NULL AND invoice_amount_grosze IS NOT NULL AND issued_on IS NOT NULL AND issued_by IS NOT NULL))
);
CREATE INDEX IF NOT EXISTS incubator_settled_idx ON incubator_invoice_entries (mode, settled_on, id);
CREATE INDEX IF NOT EXISTS incubator_issued_idx ON incubator_invoice_entries (mode, issued_on, id);
CREATE INDEX IF NOT EXISTS incubator_original_idx ON incubator_invoice_entries (original_id);
REVOKE ALL ON incubator_invoice_entries FROM PUBLIC;

-- Incremental installation on a database where the RLS gateway is already active.
DO $migration$
BEGIN
 IF to_regprocedure('wp_rls.allowed(text,jsonb,text)') IS NOT NULL THEN
  ALTER TABLE public.incubator_invoice_entries ENABLE ROW LEVEL SECURITY;
  ALTER TABLE public.incubator_invoice_entries FORCE ROW LEVEL SECURITY;
  GRANT SELECT,INSERT,UPDATE ON public.incubator_invoice_entries TO wp_rls_executor;
  GRANT SELECT ON public.incubator_invoice_entries TO wp_rls_guard,wp_rls_backup;
  REVOKE DELETE ON public.incubator_invoice_entries FROM wp_rls_executor;
  IF NOT EXISTS (SELECT 1 FROM pg_policy
                 WHERE polrelid='public.incubator_invoice_entries'::regclass AND polname='wp_read') THEN
   INSERT INTO wp_rls.previous_rls VALUES ('public.incubator_invoice_entries'::regclass, false, false)
      ON CONFLICT DO NOTHING;
   CREATE POLICY wp_guard ON public.incubator_invoice_entries FOR SELECT TO wp_rls_guard,wp_rls_backup USING (true);
   CREATE POLICY wp_read ON public.incubator_invoice_entries FOR SELECT TO wp_rls_executor
     USING (wp_rls.allowed('incubator_invoice_entries',to_jsonb(incubator_invoice_entries),'select'));
   CREATE POLICY wp_insert ON public.incubator_invoice_entries FOR INSERT TO wp_rls_executor
     WITH CHECK (wp_rls.allowed('incubator_invoice_entries',to_jsonb(incubator_invoice_entries),'insert'));
   CREATE POLICY wp_update ON public.incubator_invoice_entries FOR UPDATE TO wp_rls_executor
     USING (wp_rls.allowed('incubator_invoice_entries',to_jsonb(incubator_invoice_entries),'update'))
     WITH CHECK (wp_rls.allowed('incubator_invoice_entries',to_jsonb(incubator_invoice_entries),'update'));
  END IF;
 END IF;
END
$migration$;

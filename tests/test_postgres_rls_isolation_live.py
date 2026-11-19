"""Real PostgreSQL RLS isolation smoke test in a disposable loopback cluster.

This verifies native PostgreSQL FORCE RLS semantics only. It does NOT certify
the WiejskaPaka gateway, production migrations, or all application endpoints.
"""
import unittest

try:
    import psycopg
    import pgserver
except ImportError:
    psycopg = None
    pgserver = None


@unittest.skipUnless(psycopg is not None and pgserver is not None,
                     'Optional disposable PostgreSQL dependencies unavailable')
class LivePostgresRlsIsolation(unittest.TestCase):
    def test_gateway_migration_approved_only_in_disposable_database(self):
        import tempfile
        from pathlib import Path
        from tests.local_postgres import LocalPostgres

        sql = (Path(__file__).resolve().parents[1] /
               'database/security_rls/001_gateway.up.sql').read_text(encoding='utf-8')
        schema = (Path(__file__).resolve().parents[1] /
                  'database/postgres_schema.sql').read_text(encoding='utf-8')
        with tempfile.TemporaryDirectory(prefix='wp-rls-migration-') as folder:
            server = LocalPostgres(Path(folder) / 'cluster')
            try:
                with psycopg.connect(server.get_uri(), autocommit=True) as admin:
                    admin.execute('CREATE DATABASE wp_test_migration')
                uri = server.get_uri().replace('/postgres', '/wp_test_migration')
                with psycopg.connect(uri, autocommit=True) as admin:
                    admin.execute(schema)
                    admin.execute("SET wp_rls.disposable_test = 'yes'")
                    admin.execute(sql)
                    self.assertIsNotNone(admin.execute(
                        "SELECT to_regprocedure('wp_rls.execute(text,text)')").fetchone()[0])
                    rows = admin.execute("""
                        SELECT relname, relrowsecurity, relforcerowsecurity
                        FROM pg_class WHERE relname IN ('users', 'orders', 'sessions')
                        ORDER BY relname
                    """).fetchall()
                    self.assertEqual(len(rows), 3)
                    self.assertTrue(all(enabled and forced for _, enabled, forced in rows))
            finally:
                server.cleanup()

    def test_gateway_migration_refuses_unapproved_activation(self):
        import tempfile
        from pathlib import Path
        from tests.local_postgres import LocalPostgres

        sql = (Path(__file__).resolve().parents[1] /
               'database/security_rls/001_gateway.up.sql').read_text(encoding='utf-8')
        with tempfile.TemporaryDirectory(prefix='wp-rls-activation-') as folder:
            server = LocalPostgres(Path(folder) / 'cluster')
            try:
                with psycopg.connect(server.get_uri(), autocommit=True) as admin:
                    with self.assertRaises(psycopg.Error) as failure:
                        admin.execute(sql)
                    self.assertIn('API compatibility approval required', str(failure.exception))
                    self.assertIsNone(admin.execute(
                        "SELECT to_regnamespace('wp_rls')").fetchone()[0])
            finally:
                server.cleanup()

    def test_two_accounts_cannot_read_or_modify_each_others_orders(self):
        import tempfile
        from pathlib import Path
        from tests.local_postgres import LocalPostgres

        with tempfile.TemporaryDirectory(prefix='wp-rls-native-') as folder:
            server = LocalPostgres(Path(folder) / 'cluster')
            try:
                with psycopg.connect(server.get_uri(), autocommit=True) as admin:
                    admin.execute('CREATE ROLE wp_test_buyer LOGIN NOSUPERUSER NOBYPASSRLS')
                    admin.execute('CREATE TABLE wp_test_orders (id integer PRIMARY KEY, buyer_id integer NOT NULL, amount integer NOT NULL)')
                    admin.execute('INSERT INTO wp_test_orders VALUES (1, 101, 100), (2, 202, 200)')
                    admin.execute('ALTER TABLE wp_test_orders ENABLE ROW LEVEL SECURITY')
                    admin.execute('ALTER TABLE wp_test_orders FORCE ROW LEVEL SECURITY')
                    admin.execute('GRANT SELECT, UPDATE ON wp_test_orders TO wp_test_buyer')
                    admin.execute("""CREATE POLICY buyer_select ON wp_test_orders FOR SELECT TO wp_test_buyer
                        USING (buyer_id = NULLIF(current_setting('wp_test.actor', true), '')::integer)""")
                    admin.execute("""CREATE POLICY buyer_update ON wp_test_orders FOR UPDATE TO wp_test_buyer
                        USING (buyer_id = NULLIF(current_setting('wp_test.actor', true), '')::integer)
                        WITH CHECK (buyer_id = NULLIF(current_setting('wp_test.actor', true), '')::integer)""")
                with psycopg.connect(server.get_uri(), autocommit=True) as buyer:
                    buyer.execute('SET ROLE wp_test_buyer')
                    self.assertEqual(buyer.execute('SELECT count(*) FROM wp_test_orders').fetchone()[0], 0)
                    buyer.execute("SELECT set_config('wp_test.actor', '101', false)")
                    self.assertEqual(buyer.execute('SELECT id FROM wp_test_orders').fetchall(), [(1,)])
                    self.assertEqual(buyer.execute('UPDATE wp_test_orders SET amount=999 WHERE id=2').rowcount, 0)
                    self.assertEqual(buyer.execute('UPDATE wp_test_orders SET amount=111 WHERE id=1').rowcount, 1)
                    buyer.execute("SELECT set_config('wp_test.actor', '202', false)")
                    self.assertEqual(buyer.execute('SELECT id FROM wp_test_orders').fetchall(), [(2,)])
                with psycopg.connect(server.get_uri(), autocommit=True) as admin:
                    self.assertEqual(admin.execute('SELECT amount FROM wp_test_orders WHERE id=2').fetchone()[0], 200)

            finally:
                server.cleanup()


if __name__ == '__main__':
    unittest.main()

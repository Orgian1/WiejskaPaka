import unittest
from backend.neon_rls_preflight import inspect_rls, SENSITIVE_TABLES

class FakeConnection:
    def __init__(self, rows):
        self.rows = rows
    def execute(self, sql, params):
        assert 'pg_policy' in sql and params[0] == 'public'
        assert params[1] == list(SENSITIVE_TABLES)
        return self
    def fetchall(self):
        return self.rows

class PreflightTests(unittest.TestCase):
    def test_missing_tables_fail_closed(self):
        report = inspect_rls(FakeConnection([]))
        self.assertFalse(report['ready_for_public_launch'])
        self.assertTrue(all(x['status'] == 'missing' for x in report['tables'].values()))
    def test_disabled_rls_reported(self):
        report = inspect_rls(FakeConnection([('orders', False, False, 0)]))
        self.assertEqual(report['tables']['orders']['status'], 'rls_disabled')
    def test_policy_presence_does_not_claim_security(self):
        report = inspect_rls(FakeConnection([('orders', True, False, 2)]))
        self.assertFalse(report['ready_for_public_launch'])
        self.assertEqual(report['tables']['orders']['status'], 'manual_review_required')
    def test_enabled_without_policy_flagged(self):
        report = inspect_rls(FakeConnection([('orders', True, True, 0)]))
        self.assertEqual(report['tables']['orders']['status'], 'rls_without_policies')

if __name__ == '__main__':
    unittest.main()

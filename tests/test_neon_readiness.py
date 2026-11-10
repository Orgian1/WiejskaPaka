import unittest
from backend.neon_readiness import check_schema

class FakeCursor:
    def __init__(self, table_names, columns, role, can_create, rls):
        self.responses = [([(x,) for x in table_names]), list(columns), [role], [(can_create,)], list(rls.items())]
    def __enter__(self): return self
    def __exit__(self, *args): pass
    def execute(self, *args): self.rows = self.responses.pop(0)
    def fetchall(self): return self.rows
    def fetchone(self): return self.rows[0]

class FakeConnection:
    def __init__(self, cursor): self._cursor = cursor
    def cursor(self): return self._cursor

class NeonReadinessTests(unittest.TestCase):
    def test_missing_tables_and_columns_are_reported(self):
        conn = FakeConnection(FakeCursor(['users'], [('users','id')], (True,False,False,False,False), False, {'users':False}))
        result = check_schema(conn)
        self.assertFalse(result['schema_compatible'])
        self.assertIn('orders', result['missing_tables'])
        self.assertIn('email', result['missing_columns']['users'])
        self.assertTrue(result['limited_app_role'])
        self.assertFalse(result['production_ready'])

    def test_admin_role_is_rejected(self):
        conn = FakeConnection(FakeCursor([], [], (True,False,False,False,False), True, {}))
        self.assertFalse(check_schema(conn)['limited_app_role'])

if __name__ == '__main__': unittest.main()

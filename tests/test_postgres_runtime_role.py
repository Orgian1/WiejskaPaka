"""Pure unit tests for PostgreSQL runtime role guard (no DB required)."""
import unittest
from backend.postgres_runtime_role import assert_runtime_role


class FakeConnection:
    def __init__(self, row):
        self.row = row
        self.sql = None

    def execute(self, sql):
        self.sql = sql
        return self

    def fetchone(self):
        return self.row


class RuntimeRoleGuardTests(unittest.TestCase):
    def test_restricted_role_is_accepted(self):
        connection = FakeConnection({'elevated': False, 'owns_relations': False, 'can_create': False})
        assert_runtime_role(connection)
        self.assertIn('pg_roles', connection.sql)

    def test_rejects_each_privilege_separately(self):
        for key in ('elevated', 'owns_relations', 'can_create'):
            with self.subTest(key=key):
                row = {'elevated': False, 'owns_relations': False, 'can_create': False}
                row[key] = True
                with self.assertRaises(RuntimeError):
                    assert_runtime_role(FakeConnection(row))

    def test_rejects_missing_or_unknown_privilege_metadata(self):
        for row in (None, {}, {'elevated': False, 'owns_relations': False, 'can_create': None}):
            with self.subTest(row=row):
                with self.assertRaises(RuntimeError):
                    assert_runtime_role(FakeConnection(row))

    def test_rejects_truthy_non_boolean_metadata(self):
        with self.assertRaises(RuntimeError):
            assert_runtime_role(FakeConnection({'elevated': 0, 'owns_relations': False, 'can_create': False}))


if __name__ == '__main__':
    unittest.main()

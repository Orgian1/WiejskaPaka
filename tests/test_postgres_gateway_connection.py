"""Fail-closed connection tests with fake psycopg; no external DB."""
import sys
import types
import unittest
from contextlib import nullcontext
from unittest.mock import patch

from backend.pg_adapter import postgres_db


class Result:
    def __init__(self, installed):
        self.installed = installed

    def fetchone(self):
        return {'installed': self.installed}


class FakePg:
    def __init__(self, installed):
        self.installed = installed
        self.sql = []

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def transaction(self):
        return nullcontext()

    def execute(self, sql, params=()):
        self.sql.append(sql)
        return Result(self.installed)


class GatewayConnectionTests(unittest.TestCase):
    def run_connection(self, installed, env, *, key_ok=True, role_ok=True):
        raw = FakePg(installed)
        psycopg = types.ModuleType('psycopg')
        psycopg.connect = lambda *args, **kwargs: raw
        rows = types.ModuleType('psycopg.rows')
        rows.dict_row = object()
        with patch.dict(sys.modules, {'psycopg': psycopg, 'psycopg.rows': rows}):
            with patch.dict('os.environ', env, clear=True):
                with patch('backend.rls_gateway.load_key') as key:
                    with patch('backend.postgres_runtime_role.assert_runtime_role') as role:
                        if not key_ok:
                            key.side_effect = RuntimeError('invalid key')
                        if not role_ok:
                            role.side_effect = RuntimeError('elevated role')
                        with postgres_db('postgresql://disposable-local-only') as con:
                            self.assertEqual(con.gateway, installed)
                        return raw, key.call_count, role.call_count

    def test_legacy_schema_stays_legacy_when_not_configured(self):
        raw, key, role = self.run_connection(False, {})
        self.assertEqual((key, role), (0, 0))
        self.assertEqual(len(raw.sql), 1)

    def test_configured_gateway_missing_schema_is_rejected(self):
        for env in ({'WP_RLS_GATEWAY': '1'}, {'WP_RLS_KEY_FILE': '/unused'}):
            with self.subTest(env=env), self.assertRaisesRegex(RuntimeError, 'RLS schema required'):
                self.run_connection(False, env)

    def test_installed_gateway_requires_key_and_restricted_role(self):
        _, key, role = self.run_connection(True, {})
        self.assertEqual((key, role), (1, 1))
        with self.assertRaisesRegex(RuntimeError, 'invalid key'):
            self.run_connection(True, {}, key_ok=False)
        with self.assertRaisesRegex(RuntimeError, 'elevated role'):
            self.run_connection(True, {}, role_ok=False)


if __name__ == '__main__':
    unittest.main()

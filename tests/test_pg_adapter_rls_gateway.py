"""Verify opt-in RLS gateway routing without a live PostgreSQL database."""
import unittest
from unittest.mock import patch

from backend.pg_adapter import PgConnection


class FakeCursor:
    rowcount = 1

    def fetchone(self):
        return {'id': 12}


class FakeConnection:
    def __init__(self):
        self.calls = []

    def execute(self, sql, params=()):
        self.calls.append((sql, params))
        return FakeCursor()


class GatewayAdapterTests(unittest.TestCase):
    def test_legacy_adapter_keeps_normal_execution(self):
        raw = FakeConnection()
        result = PgConnection(raw).execute('SELECT ?', (7,))
        self.assertEqual(raw.calls, [('SELECT %s', (7,))])
        self.assertEqual(result.fetchone(), {'id': 12})

    def test_gateway_routes_translated_sql_and_params(self):
        raw = FakeConnection()
        with patch('backend.rls_gateway.execute', return_value=FakeCursor()) as gateway:
            result = PgConnection(raw, gateway=True).execute('SELECT ?', (7,))
        gateway.assert_called_once_with(raw, 'SELECT %s', (7,))
        self.assertEqual(raw.calls, [])
        self.assertEqual(result.fetchone(), {'id': 12})

    def test_gateway_preserves_insert_identity(self):
        raw = FakeConnection()
        with patch('backend.rls_gateway.execute', return_value=FakeCursor()) as gateway:
            result = PgConnection(raw, gateway=True).execute(
                'INSERT INTO users (name) VALUES (?)', ('test',))
        self.assertEqual(result.lastrowid, 12)
        self.assertIn('RETURNING id', gateway.call_args.args[1])


if __name__ == '__main__':
    unittest.main()

import unittest
from unittest.mock import patch
from contextlib import contextmanager
from datetime import datetime, timezone, timedelta
from backend.pg_adapter import postgres_verified_db
from backend.neon_session_bridge import AuthenticationFailed

NOW = datetime(2026, 10, 14, tzinfo=timezone.utc)

class Cursor:
    def __init__(self, row=None): self.row = row
    def fetchone(self): return self.row

class FakeConnection:
    def __init__(self, row):
        self.row = row
        self.calls = []
        self.transaction_open = False
    def execute(self, sql, params=()):
        assert self.transaction_open, 'query outside transaction'
        self.calls.append((sql, params))
        return Cursor(self.row)

class TestVerifiedTransaction(unittest.TestCase):
    def setUp(self):
        self.con = FakeConnection((17, NOW + timedelta(days=1)))
        self.committed = False
        self.rolled_back = False
        @contextmanager
        def fake_db(_url):
            self.con.transaction_open = True
            try:
                yield self.con
            except BaseException:
                self.rolled_back = True
                raise
            else:
                self.committed = True
            finally:
                self.con.transaction_open = False
        self.patch = patch('backend.pg_adapter.postgres_db', fake_db)
        self.patch.start()
        self.addCleanup(self.patch.stop)

    def test_identity_and_query_share_transaction(self):
        with postgres_verified_db('unused', 'Bearer valid', now=NOW) as (con, actor):
            self.assertIs(con, self.con)
            self.assertEqual(actor, 17)
            con.execute('SELECT 42')
        self.assertTrue(self.committed)
        self.assertEqual(len(self.con.calls), 4)
        self.assertIn('set_config', self.con.calls[1][0])
        self.assertEqual(self.con.calls[1][1], ('17',))
        self.assertIn('set_config', self.con.calls[-1][0])
        self.assertEqual(self.con.calls[-1][1], ())

    def test_invalid_session_aborts_transaction_without_actor(self):
        self.con.row = None
        with self.assertRaises(AuthenticationFailed):
            with postgres_verified_db('unused', 'Bearer invalid', now=NOW):
                self.fail('must not yield')
        self.assertTrue(self.rolled_back)
        self.assertEqual(len(self.con.calls), 1)

    def test_exception_rolls_back_and_clears_actor(self):
        with self.assertRaisesRegex(RuntimeError, 'abort'):
            with postgres_verified_db('unused', 'Bearer valid', now=NOW) as (con, actor):
                raise RuntimeError('abort')
        self.assertTrue(self.rolled_back)
        self.assertIn('set_config', self.con.calls[-1][0])

if __name__ == '__main__': unittest.main()

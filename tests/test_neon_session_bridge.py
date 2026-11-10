import hashlib
import unittest
from datetime import datetime, timedelta, timezone
from backend.neon_session_bridge import (
    AuthenticationFailed, authenticate_session, parse_bearer, verified_actor
)

NOW = datetime(2026, 10, 14, tzinfo=timezone.utc)


class Cursor:
    def __init__(self, row): self.row = row
    def fetchone(self): return self.row


class Connection:
    def __init__(self, row):
        self.row = row
        self.calls = []
    def execute(self, sql, params=()):
        self.calls.append((sql, params))
        return Cursor(self.row)


class TestSessionBridge(unittest.TestCase):
    def test_valid_session(self):
        con = Connection((12, NOW + timedelta(hours=1)))
        self.assertEqual(authenticate_session(con, 'Bearer secret', now=NOW), 12)
        self.assertEqual(con.calls[0][1], (hashlib.sha256(b'secret').hexdigest(),))
        self.assertNotIn('secret', con.calls[0][0])

    def test_missing_or_malformed_bearer(self):
        for header in (None, '', 'secret', 'bearer x', 'Bearer ', 'Bearer x y'):
            with self.subTest(header=header), self.assertRaises(AuthenticationFailed):
                parse_bearer(header)

    def test_missing_session(self):
        with self.assertRaises(AuthenticationFailed):
            authenticate_session(Connection(None), 'Bearer x', now=NOW)

    def test_expired_session(self):
        with self.assertRaises(AuthenticationFailed):
            authenticate_session(Connection((1, NOW)), 'Bearer x', now=NOW)

    def test_string_expiry(self):
        con = Connection((4, '2026-10-15T00:00:00+00:00'))
        self.assertEqual(authenticate_session(con, 'Bearer x', now=NOW), 4)

    def test_invalid_user(self):
        with self.assertRaises(AuthenticationFailed):
            authenticate_session(Connection((True, NOW + timedelta(days=1))), 'Bearer x', now=NOW)

    def test_context_cleaned_on_error(self):
        con = Connection((7, NOW + timedelta(days=1)))
        with self.assertRaises(RuntimeError):
            with verified_actor(con, 'Bearer x', now=NOW) as actor:
                self.assertEqual(actor, 7)
                raise RuntimeError('fail')
        self.assertEqual(len(con.calls), 3)
        self.assertIn("set_config", con.calls[-1][0])


if __name__ == '__main__': unittest.main()

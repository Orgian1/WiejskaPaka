import unittest
from datetime import datetime, timezone, timedelta
from backend.neon_session_bridge import authenticate_session, AuthenticationFailed
from backend.neon_verified_reads import my_buyer_orders, my_farmer_orders, my_courier_addresses

NOW = datetime(2026, 10, 14, tzinfo=timezone.utc)

class Cursor:
    def __init__(self, row): self.row = row
    def fetchone(self): return self.row
    def fetchall(self): return []

class Conn:
    def __init__(self, row): self.row, self.calls = row, []
    def execute(self, sql, params=()):
        self.calls.append((sql, params))
        return Cursor(self.row)

class VerifiedReadsTests(unittest.TestCase):
    def test_psycopg_dict_row_supported(self):
        c = Conn({'user_id': 17, 'expires_at': NOW + timedelta(hours=1)})
        self.assertEqual(authenticate_session(c, 'Bearer abc', now=NOW), 17)

    def test_invalid_expiry_fails_closed(self):
        for expiry in (None, 'not a timestamp', 123):
            with self.subTest(expiry=expiry), self.assertRaises((AuthenticationFailed, ValueError)):
                authenticate_session(Conn({'user_id': 17, 'expires_at': expiry}), 'Bearer abc', now=NOW)

    def test_buyer_query_uses_authenticated_id(self):
        c = Conn({'user_id': 17, 'expires_at': NOW + timedelta(hours=1)})
        self.assertEqual(my_buyer_orders(c, 'Bearer abc', now=NOW), [])
        self.assertTrue(any('WHERE buyer_id = %s' in sql and params == (17,) for sql, params in c.calls))
        self.assertIn("set_config", c.calls[-1][0])

    def test_farmer_query_uses_authenticated_id(self):
        c = Conn({'user_id': 18, 'expires_at': NOW + timedelta(hours=1)})
        my_farmer_orders(c, 'Bearer abc', now=NOW)
        self.assertTrue(any('WHERE farmer_id = %s' in sql and params == (18,) for sql, params in c.calls))

    def test_courier_query_requires_active_status(self):
        c = Conn({'user_id': 19, 'expires_at': NOW + timedelta(hours=1)})
        my_courier_addresses(c, 'Bearer abc', now=NOW)
        self.assertTrue(any('a.courier_id = %s' in sql and params == (19, 'w_drodze_testowo') for sql, params in c.calls))

    def test_no_read_after_invalid_session(self):
        c = Conn(None)
        with self.assertRaises(AuthenticationFailed):
            my_buyer_orders(c, 'Bearer abc', now=NOW)
        self.assertEqual(len(c.calls), 1)

if __name__ == '__main__': unittest.main()

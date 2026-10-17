import unittest
from backend.neon_identity import IdentityError, validate_actor_id, authenticated_actor, actor_id_sql


class FakeConnection:
    def __init__(self):
        self.calls = []
    def execute(self, query, args=()):
        self.calls.append((query, args))


class TestIdentity(unittest.TestCase):
    def test_valid(self):
        self.assertEqual(validate_actor_id(5), 5)

    def test_reject_untrusted_types(self):
        for value in (True, False, '1', None, 0, -1, 2**63):
            with self.subTest(value=value), self.assertRaises(IdentityError):
                validate_actor_id(value)

    def test_context_clears(self):
        con = FakeConnection()
        with authenticated_actor(con, 15):
            self.assertEqual(con.calls[0][1], ('15',))
        self.assertEqual(con.calls[-1][1], ())
        self.assertIn("''", con.calls[-1][0])

    def test_context_clears_on_exception(self):
        con = FakeConnection()
        with self.assertRaises(RuntimeError):
            with authenticated_actor(con, 5):
                raise RuntimeError('test')
        self.assertEqual(len(con.calls), 2)

    def test_sql_expression(self):
        self.assertIn('current_setting', actor_id_sql())


if __name__ == '__main__':
    unittest.main()

"""Unit tests for read-only PostgreSQL seller-rating RLS preflight."""
import unittest
from unittest.mock import Mock
from scripts.check_seller_ratings_postgres import check


def policy(name, command, condition=None):
    return {"policyname": name, "cmd": command, "with_check": condition, "qual": None}


class SellerRatingPostgresPreflightTests(unittest.TestCase):
    def setUp(self):
        self.connection = Mock()
        self.row = {
            "enabled": True, "forced": True, "can_read": True,
            "can_insert": True, "can_update": False, "can_delete": False,
        }
        self.policies = [
            policy("seller_ratings_read", "SELECT"),
            policy("seller_ratings_buyer_insert", "INSERT",
                   "seller_ratings.buyer_id = current_setting('wiejskapaka.actor_id') "
                   "AND status = 'odebrane'"),
        ]
        self.connection.execute.return_value.fetchone.return_value = self.row
        self.connection.execute.return_value.fetchall.return_value = self.policies

    def test_valid_configuration_is_read_only(self):
        check(self.connection)
        self.assertEqual(self.connection.execute.call_count, 2)
        for call in self.connection.execute.call_args_list:
            self.assertTrue(call.args[0].lstrip().upper().startswith("SELECT "))

    def test_missing_table_fails_closed(self):
        self.connection.execute.return_value.fetchone.return_value = None
        with self.assertRaisesRegex(RuntimeError, "nie istnieje"):
            check(self.connection)

    def test_missing_force_rls_fails_closed(self):
        self.row["forced"] = False
        with self.assertRaisesRegex(RuntimeError, "RLS"):
            check(self.connection)

    def test_missing_insert_permission_fails_closed(self):
        self.row["can_insert"] = False
        with self.assertRaisesRegex(RuntimeError, "SELECT i INSERT"):
            check(self.connection)

    def test_update_permission_fails_closed(self):
        self.row["can_update"] = True
        with self.assertRaisesRegex(RuntimeError, "UPDATE lub DELETE"):
            check(self.connection)

    def test_missing_actor_binding_fails_closed(self):
        self.policies[1]["with_check"] = "seller_ratings.buyer_id > 0 AND status = 'odebrane'"
        with self.assertRaisesRegex(RuntimeError, "actor_id"):
            check(self.connection)

    def test_missing_insert_policy_fails_closed(self):
        self.policies.pop()
        with self.assertRaisesRegex(RuntimeError, "INSERT"):
            check(self.connection)


if __name__ == "__main__":
    unittest.main()

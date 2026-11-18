"""Unit tests for read-only PostgreSQL seller-rating RLS preflight."""
import unittest
from unittest.mock import Mock
from scripts.check_seller_ratings_postgres import check


def policy(name, command, condition=None):
    return {"policyname": name, "cmd": command, "with_check": condition, "qual": None, "permissive": "PERMISSIVE"}


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
                   "AND seller_ratings.order_id > 0 AND seller_ratings.seller_id > 0 AND status = 'odebrane'"),
        ]
        self.policies[0]["qual"] = "true"
        self.role = {"rolsuper": False, "rolbypassrls": False}
        table_cursor = Mock()
        table_cursor.fetchone.return_value = self.row
        role_cursor = Mock()
        role_cursor.fetchone.return_value = self.role
        policies_cursor = Mock()
        policies_cursor.fetchall.return_value = self.policies
        self.connection.execute.side_effect = [table_cursor, role_cursor, policies_cursor]

    def test_valid_configuration_is_read_only(self):
        check(self.connection)
        self.assertEqual(self.connection.execute.call_count, 3)
        for call in self.connection.execute.call_args_list:
            self.assertTrue(call.args[0].lstrip().upper().startswith("SELECT "))

    def test_missing_table_fails_closed(self):
        self.connection.execute.side_effect[0].fetchone.return_value = None
        with self.assertRaisesRegex(RuntimeError, "nie istnieje"):
            check(self.connection)

    def test_superuser_fails_closed(self):
        self.role["rolsuper"] = True
        with self.assertRaisesRegex(RuntimeError, "SUPERUSER"):
            check(self.connection)

    def test_bypassrls_fails_closed(self):
        self.role["rolbypassrls"] = True
        with self.assertRaisesRegex(RuntimeError, "BYPASSRLS"):
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

    def test_restrictive_read_policy_fails_closed(self):
        self.policies[0]["qual"] = "buyer_id = 1"
        with self.assertRaisesRegex(RuntimeError, "podsumowania"):
            check(self.connection)

    def test_extra_policy_fails_closed(self):
        self.policies.append(policy("unsafe_insert", "INSERT", "true"))
        with self.assertRaisesRegex(RuntimeError, "Nieoczekiwane"):
            check(self.connection)

    def test_missing_order_binding_fails_closed(self):
        self.policies[1]["with_check"] = "seller_ratings.buyer_id = current_setting('wiejskapaka.actor_id') AND status = 'odebrane'"
        with self.assertRaisesRegex(RuntimeError, "order_id"):
            check(self.connection)

    def test_missing_insert_policy_fails_closed(self):
        self.policies.pop()
        with self.assertRaisesRegex(RuntimeError, "Nieoczekiwane"):
            check(self.connection)


if __name__ == "__main__":
    unittest.main()

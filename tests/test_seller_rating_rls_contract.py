"""Static fail-closed checks for the PostgreSQL seller-rating RLS migration.

These checks are not a substitute for testing policies against a real PostgreSQL
database using the deployed application role.
"""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
MIGRATION = ROOT / "migrations" / "20261118_seller_ratings_postgres.sql"
IDENTITY = ROOT / "backend" / "neon_identity.py"


class SellerRatingRlsContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sql = MIGRATION.read_text(encoding="utf-8").lower()
        cls.identity = IDENTITY.read_text(encoding="utf-8")

    def test_force_rls_and_public_revocation(self):
        self.assertIn("revoke all on table seller_ratings from public", self.sql)
        self.assertIn("alter table seller_ratings enable row level security", self.sql)
        self.assertIn("alter table seller_ratings force row level security", self.sql)

    def test_insert_is_bound_to_transaction_actor(self):
        self.assertRegex(
            self.sql,
            r"for insert with check\s*\(\s*seller_ratings\.buyer_id\s*=\s*"
            r"nullif\(current_setting\('wiejskapaka\.actor_id', true\), ''\)::bigint",
        )
        self.assertIn("set_config('wiejskapaka.actor_id', %s, true)", self.identity)

    def test_order_identity_and_final_status_are_checked(self):
        for clause in (
            "o.id = seller_ratings.order_id",
            "o.buyer_id = seller_ratings.buyer_id",
            "o.farmer_id = seller_ratings.seller_id",
            "o.status = 'odebrane'",
        ):
            with self.subTest(clause=clause):
                self.assertIn(clause, self.sql)

    def test_no_update_delete_or_public_write_grants(self):
        self.assertNotRegex(self.sql, r"create\s+policy\s+\w+\s+on\s+seller_ratings\s+for\s+(update|delete|all)")
        self.assertNotRegex(self.sql, r"grant\s+(?:all|insert|update|delete)\s+on\s+(?:table\s+)?seller_ratings\s+to\s+public")


if __name__ == "__main__":
    unittest.main()

"""Regression tests for wallet ad frequency and role separation.

Run: python -m unittest tests.test_wallet_ads_claim -v
No production payments or external services are used.
"""
import sqlite3
import unittest
from unittest.mock import patch

from backend.wallet_ads import SCHEMA_SQLITE, claim_ad


class WalletAdClaimTests(unittest.TestCase):
    def setUp(self):
        self.con = sqlite3.connect(":memory:")
        self.con.row_factory = sqlite3.Row
        self.con.execute("CREATE TABLE users (id INTEGER PRIMARY KEY)")
        self.con.executemany("INSERT INTO users(id) VALUES(?)", [(1,), (2,)])
        self.con.executescript(SCHEMA_SQLITE)
        now = 2_000_000_000
        self.now = now
        for ad_id, audience, order in [
            ("client", "klient", 0),
            ("seller", "rolnik", 0),
            ("shared", "both", 1),
        ]:
            self.con.execute(
                """INSERT INTO wallet_ads
                (id,advertiser,url,image,starts_at,ends_at,enabled,sort_order,audience,deleted)
                VALUES(?,?,?,?,?,?,?,?,?,0)""",
                (ad_id, ad_id, "https://example.invalid", "data:image/jpeg;base64,AA==",
                 now - 3600, now + 3600, 1, order, audience),
            )

    def tearDown(self):
        self.con.close()

    def test_role_targeting(self):
        with patch("backend.wallet_ads.database_now", return_value=self.now):
            client = claim_ad(self.con, 1, "client-request-001", "klient")["ad"]
            seller = claim_ad(self.con, 2, "seller-request-001", "rolnik")["ad"]
        self.assertEqual(client["id"], "client")
        self.assertEqual(seller["id"], "seller")
        self.assertEqual(client["duration_seconds"], 5)

    def test_thirty_minute_cap_and_rotation(self):
        with patch("backend.wallet_ads.database_now", return_value=self.now):
            first = claim_ad(self.con, 1, "first-request-001", "klient")["ad"]
        with patch("backend.wallet_ads.database_now", return_value=self.now + 1799):
            blocked = claim_ad(self.con, 1, "second-request-001", "klient")["ad"]
        with patch("backend.wallet_ads.database_now", return_value=self.now + 1800):
            second = claim_ad(self.con, 1, "third-request-001", "klient")["ad"]
        self.assertEqual(first["id"], "client")
        self.assertIsNone(blocked)
        self.assertEqual(second["id"], "shared")

    def test_duplicate_request_does_not_repeat(self):
        with patch("backend.wallet_ads.database_now", return_value=self.now):
            first = claim_ad(self.con, 1, "same-request-001", "klient")["ad"]
        with patch("backend.wallet_ads.database_now", return_value=self.now + 1800):
            duplicate = claim_ad(self.con, 1, "same-request-001", "klient")["ad"]
        self.assertIsNotNone(first)
        self.assertIsNone(duplicate)


if __name__ == "__main__":
    unittest.main()

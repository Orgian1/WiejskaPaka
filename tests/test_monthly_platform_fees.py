"""Unit tests for accounting summaries; no invoice is issued."""
import unittest
from backend.monthly_platform_fees import monthly_fee_summary


class MonthlyPlatformFeesTests(unittest.TestCase):
    def test_groups_small_fees_by_seller_and_kind(self):
        rows = [
            dict(seller_id=7, posted_on="2026-11-03", kind="pickup_point", amount_grosze=2000, currency="PLN"),
            dict(seller_id=7, posted_on="2026-11-12", kind="pickup_point", amount_grosze=1000, currency="PLN"),
            dict(seller_id=7, posted_on="2026-11-25", kind="seller_withdrawal_fee", amount_grosze=25, currency="PLN"),
            dict(seller_id=8, posted_on="2026-11-25", kind="pickup_point", amount_grosze=1000, currency="PLN"),
            dict(seller_id=7, posted_on="2026-12-01", kind="pickup_point", amount_grosze=1000, currency="PLN"),
        ]
        summary = monthly_fee_summary(rows, 2026, 11)
        self.assertEqual([(x["seller_id"], x["kind"], x["amount_grosze"]) for x in summary],
                         [(7, "pickup_point", 3000), (7, "seller_withdrawal_fee", 25),
                          (8, "pickup_point", 1000)])

    def test_adjustments_are_signed(self):
        entries = [
            dict(seller_id=1, posted_on="2026-11-01", kind="advertising", amount_grosze=2000, currency="PLN"),
            dict(seller_id=1, posted_on="2026-11-02", kind="advertising", amount_grosze=-500, currency="PLN"),
        ]
        self.assertEqual(monthly_fee_summary(entries, 2026, 11)[0]["amount_grosze"], 1500)

    def test_rejects_floating_point_and_unrelated_wallet_movements(self):
        row = dict(seller_id=1, posted_on="2026-11-01", kind="pickup_point", amount_grosze=20.5, currency="PLN")
        with self.assertRaises(ValueError):
            monthly_fee_summary([row], 2026, 11)
        row.update(amount_grosze=2000, kind="wallet_topup")
        with self.assertRaises(ValueError):
            monthly_fee_summary([row], 2026, 11)


if __name__ == "__main__":
    unittest.main()

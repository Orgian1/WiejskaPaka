"""Unit tests for accounting summaries; no invoice is issued."""
import unittest
from backend.monthly_platform_fees import monthly_fee_summary, monthly_fee_csv, monthly_fee_reconciliation, invoice_export_guard, monthly_fee_draft_payload, monthly_fee_audit


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

    def test_csv_keeps_exact_grosze_and_separates_sellers(self):
        entries = [
            dict(seller_id=3, posted_on="2026-11-04", kind="pickup_point", amount_grosze=1001, currency="PLN"),
            dict(seller_id=2, posted_on="2026-11-04", kind="seller_withdrawal_fee", amount_grosze=1, currency="PLN"),
        ]
        csv_data = monthly_fee_csv(entries, 2026, 11)
        self.assertEqual(csv_data.splitlines(), [
            "year,month,seller_id,currency,fee_type,transactions,amount_grosze",
            "2026,11,2,PLN,seller_withdrawal_fee,1,1",
            "2026,11,3,PLN,pickup_point,1,1001",
        ])

    def test_duplicate_source_id_cannot_be_counted_twice(self):
        row = dict(seller_id=7, posted_on="2026-11-03", kind="pickup_point",
                   amount_grosze=1000, currency="PLN", source_id="point-charge-123")
        with self.assertRaisesRegex(ValueError, "Duplicate accounting source"):
            monthly_fee_summary([row, dict(row)], 2026, 11)

    def test_distinct_refund_entry_is_allowed(self):
        original = dict(seller_id=7, posted_on="2026-11-03", kind="pickup_point",
                        amount_grosze=1000, currency="PLN", source_id="charge-1")
        refund = dict(original, amount_grosze=-1000, source_id="refund-1")
        result = monthly_fee_summary([original, refund], 2026, 11)
        self.assertEqual(result[0]["amount_grosze"], 0)
        self.assertEqual(result[0]["transactions"], 2)

    def test_rejects_ambiguous_dates_and_boolean_month(self):
        row = dict(seller_id=1, posted_on="2026-11-1", kind="pickup_point",
                   amount_grosze=1000, currency="PLN")
        with self.assertRaises(ValueError):
            monthly_fee_summary([row], 2026, 11)
        row["posted_on"] = "2026-11-01"
        with self.assertRaises(ValueError):
            monthly_fee_summary([row], 2026, True)

    def test_reconciliation_uses_single_snapshot_and_exact_control_total(self):
        entries = iter([
            dict(seller_id=1, posted_on="2026-11-02", kind="pickup_point",
                 amount_grosze=1000, currency="PLN", source_id="a"),
            dict(seller_id=2, posted_on="2026-11-03", kind="advertising",
                 amount_grosze=300, currency="PLN", source_id="b"),
            dict(seller_id=1, posted_on="2026-11-04", kind="pickup_point",
                 amount_grosze=-200, currency="PLN", source_id="c"),
        ])
        result = monthly_fee_reconciliation(entries, 2026, 11)
        self.assertEqual(result["totals"]["PLN"], {"amount_grosze": 1100, "transactions": 3})
        self.assertEqual(result["status"], "draft_unverified")
        self.assertEqual(len(result["rows"]), 2)

    def test_invoice_export_is_disabled_even_with_claimed_verification(self):
        with self.assertRaisesRegex(ValueError, "not verified"):
            invoice_export_guard({"status": "draft_unverified"})
        with self.assertRaises(NotImplementedError):
            invoice_export_guard({"status": "verified_for_invoicing"})

    def test_draft_payload_is_explicitly_non_fiscal(self):
        row = dict(seller_id=4, posted_on="2026-11-03", kind="advertising",
                   amount_grosze=250, currency="PLN", source_id="ad-4")
        payload = monthly_fee_draft_payload([row], 2026, 11)
        self.assertEqual(payload["schema_version"], 1)
        self.assertEqual(payload["document_type"], "internal_monthly_fee_draft")
        self.assertFalse(payload["fiscal_document"])
        self.assertEqual(payload["control_totals"]["PLN"]["amount_grosze"], 250)
        self.assertNotIn("invoice_number", payload)
        self.assertNotIn("vat_rate", payload)

    def test_audit_requires_traceable_source_ids(self):
        row = dict(seller_id=1, posted_on="2026-11-02", kind="pickup_point",
                   amount_grosze=1000, currency="PLN")
        with self.assertRaisesRegex(ValueError, "source_id"):
            monthly_fee_audit([row], 2026, 11)
        row["source_id"] = "point-1"
        report = monthly_fee_audit([row], 2026, 11)
        self.assertTrue(report["traceable"])
        self.assertEqual(report["source_count"], 1)

    def test_rejects_floating_point_and_unrelated_wallet_movements(self):
        row = dict(seller_id=1, posted_on="2026-11-01", kind="pickup_point", amount_grosze=20.5, currency="PLN")
        with self.assertRaises(ValueError):
            monthly_fee_summary([row], 2026, 11)
        row.update(amount_grosze=2000, kind="wallet_topup")
        with self.assertRaises(ValueError):
            monthly_fee_summary([row], 2026, 11)


if __name__ == "__main__":
    unittest.main()

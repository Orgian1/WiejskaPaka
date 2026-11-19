import sqlite3
import unittest

from backend.platform_fee_ledger import (
    add_platform_fee_entry, initialize_platform_fee_ledger, monthly_platform_fee_entries,
    monthly_platform_fee_draft,
)
from backend.monthly_platform_fees import monthly_fee_audit, invoice_export_guard


class PlatformFeeLedgerTests(unittest.TestCase):
    def setUp(self):
        self.con = sqlite3.connect(":memory:")
        self.con.execute("PRAGMA foreign_keys = ON")
        initialize_platform_fee_ledger(self.con)

    def tearDown(self):
        self.con.close()

    def add(self, **overrides):
        entry = dict(source_id="pickup:1", seller_id=7, posted_on="2026-11-19",
                     kind="pickup_point", amount_grosze=1000)
        entry.update(overrides)
        add_platform_fee_entry(self.con, **entry)

    def test_report_groups_fees_and_corrections_without_floats(self):
        self.add()
        self.add(source_id="pickup:refund:1", amount_grosze=-250, correction_of="pickup:1")
        self.add(source_id="ad:2", kind="advertising", amount_grosze=3500)
        report = monthly_fee_audit(monthly_platform_fee_entries(self.con, 2026, 11), 2026, 11)
        self.assertEqual(report["source_count"], 3)
        self.assertEqual(report["totals"]["PLN"]["amount_grosze"], 4250)
        self.assertEqual(len(report["rows"]), 2)

    def test_duplicate_source_id_is_rejected_without_double_charge(self):
        self.add()
        with self.assertRaises(sqlite3.IntegrityError):
            self.add()
        self.assertEqual(len(monthly_platform_fee_entries(self.con, 2026, 11)), 1)

    def test_correction_requires_matching_original(self):
        self.add()
        for data in (
            dict(source_id="x", seller_id=8, amount_grosze=-100, correction_of="pickup:1"),
            dict(source_id="y", kind="advertising", amount_grosze=-100, correction_of="pickup:1"),
            dict(source_id="z", amount_grosze=-100, correction_of="missing"),
        ):
            with self.assertRaisesRegex(ValueError, "Correction"):
                self.add(**data)

    def test_direct_sql_rejects_invalid_posting_dates(self):
        for i, value in enumerate(("2026-02-30", "2026-11-1", "not-a-date")):
            with self.subTest(value=value):
                with self.assertRaisesRegex(sqlite3.IntegrityError, "Invalid ledger posting date"):
                    self.con.execute("""
                        INSERT INTO platform_fee_ledger
                            (source_id, seller_id, posted_on, kind, amount_grosze)
                        VALUES (?, 7, ?, 'pickup_point', 1000)
                    """, (f"bad-date:{i}", value))
        self.assertEqual(monthly_platform_fee_entries(self.con, 2026, 11), [])

    def test_direct_sql_correction_cannot_cross_seller_or_fee_kind(self):
        self.add()
        for source, seller, kind in (
            ("refund:wrong-seller", 8, "pickup_point"),
            ("refund:wrong-kind", 7, "advertising"),
        ):
            with self.subTest(source=source):
                with self.assertRaisesRegex(sqlite3.IntegrityError, "match original"):
                    self.con.execute("""
                        INSERT INTO platform_fee_ledger
                            (source_id, seller_id, posted_on, kind, amount_grosze, correction_of)
                        VALUES (?, ?, '2026-11-19', ?, -100, 'pickup:1')
                    """, (source, seller, kind))
        self.assertEqual(len(monthly_platform_fee_entries(self.con, 2026, 11)), 1)

    def test_direct_sql_cannot_bypass_refund_limit(self):
        self.add()
        self.add(source_id="refund:1", amount_grosze=-700, correction_of="pickup:1")
        with self.assertRaisesRegex(sqlite3.IntegrityError, "exceed original"):
            self.con.execute("""
                INSERT INTO platform_fee_ledger
                    (source_id, seller_id, posted_on, kind, amount_grosze, correction_of)
                VALUES ('refund:2', 7, '2026-11-19', 'pickup_point', -400, 'pickup:1')
            """)
        self.assertEqual(len(monthly_platform_fee_entries(self.con, 2026, 11)), 2)

    def test_direct_sql_cannot_add_positive_correction(self):
        self.add()
        with self.assertRaisesRegex(sqlite3.IntegrityError, "Correction must be negative"):
            self.con.execute("""
                INSERT INTO platform_fee_ledger
                    (source_id, seller_id, posted_on, kind, amount_grosze, correction_of)
                VALUES ('refund:positive', 7, '2026-11-19', 'pickup_point', 100, 'pickup:1')
            """)

    def test_ledger_entries_cannot_be_modified_or_deleted(self):
        self.add()
        with self.assertRaisesRegex(sqlite3.IntegrityError, "immutable"):
            self.con.execute("UPDATE platform_fee_ledger SET amount_grosze = 1 WHERE source_id = 'pickup:1'")
        with self.assertRaisesRegex(sqlite3.IntegrityError, "immutable"):
            self.con.execute("DELETE FROM platform_fee_ledger WHERE source_id = 'pickup:1'")
        self.assertEqual(monthly_platform_fee_entries(self.con, 2026, 11)[0]["amount_grosze"], 1000)

    def test_positive_correction_is_rejected(self):
        self.add()
        with self.assertRaisesRegex(ValueError, "Positive adjustments"):
            self.add(source_id="correction:plus", amount_grosze=500, correction_of="pickup:1")
        self.assertEqual(len(monthly_platform_fee_entries(self.con, 2026, 11)), 1)

    def test_multiple_refunds_cannot_exceed_original_fee(self):
        self.add()
        self.add(source_id="refund:1", amount_grosze=-700, correction_of="pickup:1")
        with self.assertRaisesRegex(ValueError, "exceed original"):
            self.add(source_id="refund:2", amount_grosze=-400, correction_of="pickup:1")
        self.add(source_id="refund:3", amount_grosze=-300, correction_of="pickup:1")
        report = monthly_fee_audit(monthly_platform_fee_entries(self.con, 2026, 11), 2026, 11)
        self.assertEqual(report["totals"]["PLN"]["amount_grosze"], 0)

    def test_negative_without_correction_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Negative fees"):
            self.add(amount_grosze=-100)

    def test_rejects_boolean_and_float_amounts(self):
        for value in (True, 1000.0, 0):
            with self.assertRaises(ValueError):
                self.add(amount_grosze=value)

    def test_invalid_date_and_seller_are_rejected(self):
        for data in (dict(posted_on="2026-02-30"), dict(seller_id=True),
                     dict(source_id="  "), dict(kind="delivery")):
            with self.assertRaises(ValueError):
                self.add(**data)

    def test_refund_of_refund_is_rejected(self):
        self.add()
        self.add(source_id="refund:1", amount_grosze=-300, correction_of="pickup:1")
        with self.assertRaisesRegex(ValueError, "Correction must refer to matching fee"):
            self.add(source_id="refund:2", amount_grosze=-100, correction_of="refund:1")
        self.assertEqual(len(monthly_platform_fee_entries(self.con, 2026, 11)), 2)

    def test_invalid_report_periods_fail_closed(self):
        for year, month in ((2026, 0), (2026, 13), (9999, 12), (True, 11), (2026, False)):
            with self.subTest(year=year, month=month):
                with self.assertRaises(ValueError):
                    monthly_platform_fee_entries(self.con, year, month)

    def test_december_and_january_reports_do_not_overlap(self):
        self.add(posted_on="2026-12-31")
        self.add(source_id="pickup:jan", posted_on="2027-01-01", amount_grosze=2500)
        december = monthly_platform_fee_draft(self.con, 2026, 12)
        january = monthly_platform_fee_draft(self.con, 2027, 1)
        self.assertEqual(december["control_totals"]["PLN"]["amount_grosze"], 1000)
        self.assertEqual(january["control_totals"]["PLN"]["amount_grosze"], 2500)
        self.assertEqual(len(december["rows"]), 1)
        self.assertEqual(len(january["rows"]), 1)

    def test_monthly_ledger_draft_cannot_be_exported_as_invoice(self):
        self.add()
        draft = monthly_platform_fee_draft(self.con, 2026, 11)
        with self.assertRaises((ValueError, NotImplementedError)):
            invoice_export_guard(draft)

    def test_monthly_draft_separates_sellers_and_fee_kinds(self):
        self.add()
        self.add(source_id="pickup:second", seller_id=8, amount_grosze=2000)
        self.add(source_id="ad:first", seller_id=7, kind="advertising", amount_grosze=3500)
        draft = monthly_platform_fee_draft(self.con, 2026, 11)
        self.assertEqual(len(draft["rows"]), 3)
        values = {(row["seller_id"], row["kind"]): row["amount_grosze"] for row in draft["rows"]}
        self.assertEqual(values, {
            (7, "pickup_point"): 1000,
            (8, "pickup_point"): 2000,
            (7, "advertising"): 3500,
        })
        self.assertEqual(draft["control_totals"]["PLN"]["amount_grosze"], 6500)

    def test_monthly_draft_is_deterministic_and_read_only(self):
        self.add()
        before = self.con.total_changes
        first = monthly_platform_fee_draft(self.con, 2026, 11)
        second = monthly_platform_fee_draft(self.con, 2026, 11)
        self.assertEqual(first, second)
        self.assertEqual(self.con.total_changes, before)

    def test_empty_month_draft_remains_non_fiscal(self):
        draft = monthly_platform_fee_draft(self.con, 2026, 12)
        self.assertEqual(draft["rows"], [])
        self.assertFalse(draft["fiscal_document"])
        self.assertFalse(draft["payment_provider_confirmed"])

    def test_monthly_draft_is_not_invoice_or_payment_confirmation(self):
        self.add()
        draft = monthly_platform_fee_draft(self.con, 2026, 11)
        self.assertEqual(draft["document_type"], "internal_monthly_fee_draft")
        self.assertEqual(draft["status"], "draft_unverified")
        self.assertFalse(draft["fiscal_document"])
        self.assertFalse(draft["payment_provider_confirmed"])
        self.assertEqual(draft["source_system"], "platform_fee_ledger")

    def test_refund_in_later_month_is_reported_in_refund_month(self):
        self.add(posted_on="2026-11-30")
        self.add(source_id="refund:december", posted_on="2026-12-01",
                 amount_grosze=-1000, correction_of="pickup:1")
        november = monthly_fee_audit(monthly_platform_fee_entries(self.con, 2026, 11), 2026, 11)
        december = monthly_fee_audit(monthly_platform_fee_entries(self.con, 2026, 12), 2026, 12)
        self.assertEqual(november["totals"]["PLN"]["amount_grosze"], 1000)
        self.assertEqual(december["totals"]["PLN"]["amount_grosze"], -1000)
        self.assertEqual(november["source_count"], 1)
        self.assertEqual(december["source_count"], 1)

    def test_initialization_is_idempotent_and_keeps_existing_fees(self):
        self.add()
        initialize_platform_fee_ledger(self.con)
        initialize_platform_fee_ledger(self.con)
        self.assertEqual(len(monthly_platform_fee_entries(self.con, 2026, 11)), 1)
        with self.assertRaisesRegex(sqlite3.IntegrityError, "immutable"):
            self.con.execute("DELETE FROM platform_fee_ledger WHERE source_id = 'pickup:1'")
        with self.assertRaises(sqlite3.IntegrityError):
            self.add()

    def test_monthly_read_is_read_only(self):
        self.add()
        before = self.con.total_changes
        first = monthly_platform_fee_entries(self.con, 2026, 11)
        self.assertEqual(first, monthly_platform_fee_entries(self.con, 2026, 11))
        self.assertEqual(self.con.total_changes, before)
        self.assertEqual(monthly_platform_fee_entries(self.con, 2026, 12), [])


if __name__ == "__main__":
    unittest.main()

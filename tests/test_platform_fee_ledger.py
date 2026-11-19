import sqlite3
import unittest

from backend.platform_fee_ledger import (
    add_platform_fee_entry, initialize_platform_fee_ledger, monthly_platform_fee_entries,
)
from backend.monthly_platform_fees import monthly_fee_audit


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

    def test_monthly_read_is_read_only(self):
        self.add()
        before = self.con.total_changes
        first = monthly_platform_fee_entries(self.con, 2026, 11)
        self.assertEqual(first, monthly_platform_fee_entries(self.con, 2026, 11))
        self.assertEqual(self.con.total_changes, before)
        self.assertEqual(monthly_platform_fee_entries(self.con, 2026, 12), [])


if __name__ == "__main__":
    unittest.main()

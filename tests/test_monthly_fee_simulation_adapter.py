import sqlite3
import unittest
from backend.monthly_fee_simulation_adapter import simulated_withdrawal_fee_entries, simulated_monthly_fee_report, simulated_monthly_withdrawal_report
from backend.monthly_platform_fees import monthly_fee_audit


class SimulatedWithdrawalFeeAdapterTests(unittest.TestCase):
    def test_missing_terms_do_not_silently_disappear(self):
        con = sqlite3.connect(":memory:")
        con.row_factory = sqlite3.Row
        con.executescript("""
            CREATE TABLE wallet_preview_resolutions
              (id TEXT, withdrawal_id TEXT, user_id INTEGER, created_at INTEGER, state TEXT);
            CREATE TABLE wallet_preview_terms
              (withdrawal_id TEXT, owner_role TEXT, fee_basis_points INTEGER,
               fee_grosze INTEGER, gross_grosze INTEGER, net_grosze INTEGER);
            CREATE TABLE wallet_preview_entries (id TEXT, kind TEXT, user_id INTEGER);
            INSERT INTO wallet_preview_entries VALUES ('w1','withdrawal',3);
            INSERT INTO wallet_preview_resolutions VALUES
              ('r1','w1',3,1793577600,'completed_test');
        """)
        with self.assertRaisesRegex(ValueError, "Missing simulated withdrawal source"):
            simulated_withdrawal_fee_entries(con, 2026, 11)
        con.close()

    def test_two_resolutions_for_same_withdrawal_are_rejected(self):
        con = sqlite3.connect(":memory:")
        con.row_factory = sqlite3.Row
        con.executescript("""
            CREATE TABLE wallet_preview_resolutions
              (id TEXT, withdrawal_id TEXT, user_id INTEGER, created_at INTEGER, state TEXT);
            CREATE TABLE wallet_preview_terms
              (withdrawal_id TEXT, owner_role TEXT, fee_basis_points INTEGER,
               fee_grosze INTEGER, gross_grosze INTEGER, net_grosze INTEGER);
            CREATE TABLE wallet_preview_entries (id TEXT, kind TEXT, user_id INTEGER);
            INSERT INTO wallet_preview_entries VALUES ('w1','withdrawal',3);
            INSERT INTO wallet_preview_terms VALUES ('w1','rolnik',500,100,2000,1900);
            INSERT INTO wallet_preview_resolutions VALUES
              ('r1','w1',3,1793577600,'completed_test'),
              ('r2','w1',3,1793577600,'completed_test');
        """)
        with self.assertRaisesRegex(ValueError, "Duplicate simulated withdrawal ID"):
            simulated_withdrawal_fee_entries(con, 2026, 11)
        con.close()

    def test_invalid_reporting_period_is_rejected(self):
        con = sqlite3.connect(":memory:")
        for year, month in [(2026, 13), (2026, 0), ("2026", 11), (True, 11), (2026, 11.0)]:
            with self.subTest(year=year, month=month):
                with self.assertRaises(ValueError):
                    simulated_withdrawal_fee_entries(con, year, month)
        con.close()

    def test_report_filters_multiple_months_without_double_counting(self):
        from datetime import datetime, timezone
        con = sqlite3.connect(":memory:")
        con.row_factory = sqlite3.Row
        con.executescript("""
            CREATE TABLE wallet_preview_resolutions
              (id TEXT, withdrawal_id TEXT, user_id INTEGER, created_at INTEGER, state TEXT);
            CREATE TABLE wallet_preview_terms
              (withdrawal_id TEXT, owner_role TEXT, fee_basis_points INTEGER,
               fee_grosze INTEGER, gross_grosze INTEGER, net_grosze INTEGER);
            CREATE TABLE wallet_preview_entries (id TEXT, kind TEXT, user_id INTEGER);
            INSERT INTO wallet_preview_entries VALUES ('w1','withdrawal',3),('w2','withdrawal',3);
            INSERT INTO wallet_preview_terms VALUES
              ('w1','rolnik',500,100,2000,1900),('w2','rolnik',500,200,4000,3800);
        """)
        november = int(datetime(2026, 11, 30, 23, 59, tzinfo=timezone.utc).timestamp())
        december = int(datetime(2026, 12, 1, 0, 0, tzinfo=timezone.utc).timestamp())
        con.executemany("INSERT INTO wallet_preview_resolutions VALUES (?,?,?,?,?)", [
            ("r1", "w1", 3, november, "completed_test"),
            ("r2", "w2", 3, december, "completed_test"),
        ])
        november_rows = simulated_withdrawal_fee_entries(con, 2026, 11)
        december_rows = simulated_withdrawal_fee_entries(con, 2026, 12)
        self.assertEqual([row["amount_grosze"] for row in november_rows], [100])
        self.assertEqual([row["amount_grosze"] for row in december_rows], [200])
        self.assertTrue(set(row["source_id"] for row in november_rows).isdisjoint(
            row["source_id"] for row in december_rows))
        con.close()

    def test_invalid_completion_timestamp_is_rejected(self):
        con = sqlite3.connect(":memory:")
        con.row_factory = sqlite3.Row
        con.executescript("""
            CREATE TABLE wallet_preview_resolutions
              (id TEXT, withdrawal_id TEXT, user_id INTEGER, created_at INTEGER, state TEXT);
            CREATE TABLE wallet_preview_terms
              (withdrawal_id TEXT, owner_role TEXT, fee_basis_points INTEGER,
               fee_grosze INTEGER, gross_grosze INTEGER, net_grosze INTEGER);
            CREATE TABLE wallet_preview_entries (id TEXT, kind TEXT, user_id INTEGER);
            INSERT INTO wallet_preview_entries VALUES ('w1','withdrawal',3);
            INSERT INTO wallet_preview_terms VALUES ('w1','rolnik',500,100,2000,1900);
            INSERT INTO wallet_preview_resolutions VALUES
              ('r1','w1',3,-1,'completed_test');
        """)
        with self.assertRaisesRegex(ValueError, "timestamp"):
            simulated_withdrawal_fee_entries(con, 2026, 11)
        con.close()

    def test_missing_source_tables_fail_instead_of_reporting_zero(self):
        con = sqlite3.connect(":memory:")
        con.row_factory = sqlite3.Row
        with self.assertRaises(sqlite3.OperationalError):
            simulated_withdrawal_fee_entries(con, 2026, 11)
        con.close()

    def test_empty_initialized_source_has_no_fees(self):
        con = sqlite3.connect(":memory:")
        con.row_factory = sqlite3.Row
        con.executescript("""
            CREATE TABLE wallet_preview_resolutions
              (id TEXT, withdrawal_id TEXT, user_id INTEGER, created_at INTEGER, state TEXT);
            CREATE TABLE wallet_preview_terms
              (withdrawal_id TEXT, owner_role TEXT, fee_basis_points INTEGER,
               fee_grosze INTEGER, gross_grosze INTEGER, net_grosze INTEGER);
            CREATE TABLE wallet_preview_entries (id TEXT, kind TEXT, user_id INTEGER);
        """)
        self.assertEqual(simulated_withdrawal_fee_entries(con, 2026, 11), [])
        con.close()

    def test_duplicate_resolution_is_rejected(self):
        con = sqlite3.connect(":memory:")
        con.row_factory = sqlite3.Row
        con.executescript("""
            CREATE TABLE wallet_preview_resolutions
              (id TEXT, withdrawal_id TEXT, user_id INTEGER, created_at INTEGER, state TEXT);
            CREATE TABLE wallet_preview_terms
              (withdrawal_id TEXT, owner_role TEXT, fee_basis_points INTEGER,
               fee_grosze INTEGER, gross_grosze INTEGER, net_grosze INTEGER);
            CREATE TABLE wallet_preview_entries (id TEXT, kind TEXT, user_id INTEGER);
            INSERT INTO wallet_preview_entries VALUES ('w1','withdrawal',3),('w2','withdrawal',3);
            INSERT INTO wallet_preview_terms VALUES
              ('w1','rolnik',500,100,2000,1900),('w2','rolnik',500,100,2000,1900);
            INSERT INTO wallet_preview_resolutions VALUES
              ('duplicate','w1',3,1793577600,'completed_test'),
              ('duplicate','w2',3,1793577600,'completed_test');
        """)
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            simulated_withdrawal_fee_entries(con, 2026, 11)
        con.close()

    def test_corrupt_fee_and_wrong_owner_fail_closed(self):
        con = sqlite3.connect(":memory:")
        con.row_factory = sqlite3.Row
        con.executescript("""
            CREATE TABLE wallet_preview_resolutions
              (id TEXT, withdrawal_id TEXT, user_id INTEGER, created_at INTEGER, state TEXT);
            CREATE TABLE wallet_preview_terms
              (withdrawal_id TEXT, owner_role TEXT, fee_basis_points INTEGER,
               fee_grosze INTEGER, gross_grosze INTEGER, net_grosze INTEGER);
            CREATE TABLE wallet_preview_entries (id TEXT, kind TEXT, user_id INTEGER);
            INSERT INTO wallet_preview_entries VALUES ('w1','withdrawal',3);
            INSERT INTO wallet_preview_terms VALUES ('w1','rolnik',500,999,2000,1001);
            INSERT INTO wallet_preview_resolutions VALUES
              ('r1','w1',3,1793577600,'completed_test');
        """)
        with self.assertRaisesRegex(ValueError, "fee mismatch"):
            simulated_withdrawal_fee_entries(con, 2026, 11)
        con.execute("UPDATE wallet_preview_terms SET fee_grosze=100, net_grosze=1900")
        con.execute("UPDATE wallet_preview_resolutions SET user_id=4")
        with self.assertRaisesRegex(ValueError, "owner mismatch"):
            simulated_withdrawal_fee_entries(con, 2026, 11)
        con.close()

    def test_zero_fee_is_not_a_charge(self):
        con = sqlite3.connect(":memory:")
        con.row_factory = sqlite3.Row
        con.executescript("""
            CREATE TABLE wallet_preview_resolutions
              (id TEXT, withdrawal_id TEXT, user_id INTEGER, created_at INTEGER, state TEXT);
            CREATE TABLE wallet_preview_terms
              (withdrawal_id TEXT, owner_role TEXT, fee_basis_points INTEGER, fee_grosze INTEGER, gross_grosze INTEGER, net_grosze INTEGER);
            CREATE TABLE wallet_preview_entries (id TEXT, kind TEXT, user_id INTEGER);
            INSERT INTO wallet_preview_entries VALUES ('w1','withdrawal',3);
            INSERT INTO wallet_preview_terms VALUES ('w1','rolnik',500,0,1,1);
            INSERT INTO wallet_preview_resolutions VALUES
              ('r1','w1',3,1793577600,'completed_test');
        """)
        self.assertEqual(simulated_withdrawal_fee_entries(con, 2026, 11), [])
        con.close()

    def test_utc_month_boundary_uses_completion_timestamp(self):
        con = sqlite3.connect(":memory:")
        con.row_factory = sqlite3.Row
        con.executescript("""
            CREATE TABLE wallet_preview_resolutions
              (id TEXT, withdrawal_id TEXT, user_id INTEGER, created_at INTEGER, state TEXT);
            CREATE TABLE wallet_preview_terms
              (withdrawal_id TEXT, owner_role TEXT, fee_basis_points INTEGER, fee_grosze INTEGER, gross_grosze INTEGER, net_grosze INTEGER);
            CREATE TABLE wallet_preview_entries (id TEXT, kind TEXT, user_id INTEGER);
            INSERT INTO wallet_preview_entries VALUES ('w1','withdrawal',3);
            INSERT INTO wallet_preview_terms VALUES ('w1','rolnik',500,100,2000,1900);
        """)
        from datetime import datetime, timezone
        timestamp = int(datetime(2026, 12, 1, 0, 0, tzinfo=timezone.utc).timestamp())
        con.execute("INSERT INTO wallet_preview_resolutions VALUES (?,?,?,?,?)",
                    ("r1", "w1", 3, timestamp, "completed_test"))
        self.assertEqual(simulated_withdrawal_fee_entries(con, 2026, 11), [])
        december = simulated_withdrawal_fee_entries(con, 2026, 12)
        self.assertEqual(len(december), 1)
        self.assertEqual(december[0]["posted_on"], "2026-12-01")
        con.close()

    def test_only_completed_seller_withdrawals_are_included(self):
        con = sqlite3.connect(":memory:")
        con.row_factory = sqlite3.Row
        con.executescript("""
            CREATE TABLE wallet_preview_resolutions
              (id TEXT, withdrawal_id TEXT, user_id INTEGER, created_at INTEGER, state TEXT);
            CREATE TABLE wallet_preview_terms
              (withdrawal_id TEXT, owner_role TEXT, fee_basis_points INTEGER, fee_grosze INTEGER, gross_grosze INTEGER, net_grosze INTEGER);
            CREATE TABLE wallet_preview_entries (id TEXT, kind TEXT, user_id INTEGER);
            INSERT INTO wallet_preview_entries VALUES ('w1','withdrawal',3),('w2','withdrawal',3),
              ('w3','withdrawal',4),('w4','withdrawal',3);
            INSERT INTO wallet_preview_terms VALUES
              ('w1','rolnik',500,125,2500,2375),('w2','rolnik',500,100,2000,1900),
              ('w3','klient',0,0,2000,2000),('w4','rolnik',500,50,1000,950);
            INSERT INTO wallet_preview_resolutions VALUES
              ('r1','w1',3,1793577600,'completed_test'),
              ('r2','w2',3,1793577600,'cancelled_test'),
              ('r3','w3',4,1793577600,'completed_test'),
              ('r4','w4',3,1793577600,'completed_test');
        """)
        entries = simulated_withdrawal_fee_entries(con, 2026, 11)
        self.assertEqual(len(entries), 2)
        self.assertEqual(sum(row["amount_grosze"] for row in entries), 175)
        report = monthly_fee_audit(entries, 2026, 11)
        self.assertEqual(report["totals"]["PLN"]["amount_grosze"], 175)
        self.assertTrue(all(row["source_id"].startswith("simulation:") for row in entries))
        wrapped = simulated_monthly_withdrawal_report(con, 2026, 11)
        self.assertEqual(wrapped["environment"], "simulation_only")
        self.assertFalse(wrapped["fiscal_document"])
        self.assertFalse(wrapped["bank_transfer_executed"])
        draft = simulated_monthly_fee_report(con, 2026, 11)
        self.assertEqual(draft["environment"], "simulation_only")
        self.assertFalse(draft["fiscal_document"])
        self.assertFalse(draft["payment_provider_confirmed"])
        con.close()


if __name__ == "__main__":
    unittest.main()

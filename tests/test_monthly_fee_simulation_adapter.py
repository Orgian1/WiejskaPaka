import sqlite3
import unittest
from backend.monthly_fee_simulation_adapter import simulated_withdrawal_fee_entries, simulated_monthly_fee_report, simulated_monthly_withdrawal_report
from backend.monthly_platform_fees import monthly_fee_audit


class SimulatedWithdrawalFeeAdapterTests(unittest.TestCase):
    def test_zero_fee_is_not_a_charge(self):
        con = sqlite3.connect(":memory:")
        con.row_factory = sqlite3.Row
        con.executescript("""
            CREATE TABLE wallet_preview_resolutions
              (id TEXT, withdrawal_id TEXT, user_id INTEGER, created_at INTEGER, state TEXT);
            CREATE TABLE wallet_preview_terms
              (withdrawal_id TEXT, owner_role TEXT, fee_basis_points INTEGER, fee_grosze INTEGER);
            CREATE TABLE wallet_preview_entries (id TEXT, kind TEXT);
            INSERT INTO wallet_preview_entries VALUES ('w1','withdrawal');
            INSERT INTO wallet_preview_terms VALUES ('w1','rolnik',500,0);
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
              (withdrawal_id TEXT, owner_role TEXT, fee_basis_points INTEGER, fee_grosze INTEGER);
            CREATE TABLE wallet_preview_entries (id TEXT, kind TEXT);
            INSERT INTO wallet_preview_entries VALUES ('w1','withdrawal');
            INSERT INTO wallet_preview_terms VALUES ('w1','rolnik',500,100);
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
              (withdrawal_id TEXT, owner_role TEXT, fee_basis_points INTEGER, fee_grosze INTEGER);
            CREATE TABLE wallet_preview_entries (id TEXT, kind TEXT);
            INSERT INTO wallet_preview_entries VALUES ('w1','withdrawal'),('w2','withdrawal'),
              ('w3','withdrawal'),('w4','withdrawal');
            INSERT INTO wallet_preview_terms VALUES
              ('w1','rolnik',500,125),('w2','rolnik',500,100),
              ('w3','klient',0,0),('w4','rolnik',500,50);
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

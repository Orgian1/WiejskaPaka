import sqlite3
import unittest
from backend.monthly_fee_simulation_adapter import simulated_withdrawal_fee_entries
from backend.monthly_platform_fees import monthly_fee_audit


class SimulatedWithdrawalFeeAdapterTests(unittest.TestCase):
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
        con.close()


if __name__ == "__main__":
    unittest.main()

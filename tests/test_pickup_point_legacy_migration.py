import sqlite3
import unittest
from datetime import datetime
from zoneinfo import ZoneInfo
from backend.pickup_point_periods import SCHEMA
from backend.pickup_point_legacy_migration import import_verified_legacy_period

class LegacyMigrationTests(unittest.TestCase):
    def setUp(self):
        self.con=sqlite3.connect(':memory:')
        self.con.row_factory=sqlite3.Row
        self.con.executescript('''CREATE TABLE users(id INTEGER PRIMARY KEY);
            CREATE TABLE pickup_points(id INTEGER PRIMARY KEY,farmer_id INTEGER,active INTEGER);
            CREATE TABLE wallet_preview_entries(id TEXT,user_id INTEGER,kind TEXT,state TEXT,amount_grosze INTEGER);
            INSERT INTO users VALUES(1),(2);
            INSERT INTO pickup_points VALUES(7,1,1);
            INSERT INTO wallet_preview_entries VALUES('topup',1,'topup','credited',1000);''')
        self.con.executescript(SCHEMA)
        self.start=datetime(2026,11,18,12,tzinfo=ZoneInfo('Europe/Warsaw'))
    def tearDown(self): self.con.close()
    def test_missing_verified_debit_cannot_activate(self):
        for entry in ('missing','topup'):
            with self.assertRaises(ValueError):
                import_verified_legacy_period(self.con,point_id=7,farmer_id=1,
                    starts_at=self.start,wallet_entry_id=entry,dry_run=False)
        self.assertEqual(self.con.execute('SELECT COUNT(*) FROM pickup_point_periods').fetchone()[0],0)
    def test_dry_run_and_verified_import(self):
        self.con.execute("INSERT INTO wallet_preview_entries VALUES('paid',1,'point_fee','charged',1000)")
        args=dict(point_id=7,farmer_id=1,starts_at=self.start,wallet_entry_id='paid')
        self.assertEqual(import_verified_legacy_period(self.con,**args)['status'],'dry_run')
        self.assertEqual(self.con.execute('SELECT COUNT(*) FROM pickup_point_periods').fetchone()[0],0)
        self.assertEqual(import_verified_legacy_period(self.con,**args,dry_run=False)['status'],'imported')
        self.assertEqual(import_verified_legacy_period(self.con,**args,dry_run=False)['status'],'already_imported')
        self.assertEqual(self.con.execute('SELECT COUNT(*) FROM pickup_point_periods').fetchone()[0],1)
    def test_rejects_overlapping_future_period(self):
        from datetime import timedelta
        from backend.pickup_point_periods import period_end
        future=self.start+timedelta(days=10)
        self.con.execute("INSERT INTO pickup_point_periods VALUES(?,?,?,?,?,0,'promotion',NULL)",
            ('future',7,1,future.isoformat(),period_end(future).isoformat()))
        self.con.execute("INSERT INTO wallet_preview_entries VALUES('paid',1,'point_fee','charged',1000)")
        with self.assertRaises(ValueError):
            import_verified_legacy_period(self.con,point_id=7,farmer_id=1,
                starts_at=self.start,wallet_entry_id='paid',dry_run=False)
        self.assertEqual(self.con.execute('SELECT COUNT(*) FROM pickup_point_periods').fetchone()[0],1)
    def test_same_wallet_debit_cannot_pay_for_two_points(self):
        self.con.execute("INSERT INTO pickup_points VALUES(8,1,1)")
        self.con.execute("INSERT INTO wallet_preview_entries VALUES('paid',1,'point_fee','charged',1000)")
        import_verified_legacy_period(self.con,point_id=7,farmer_id=1,
            starts_at=self.start,wallet_entry_id='paid',dry_run=False)
        with self.assertRaisesRegex(ValueError,'another pickup point'):
            import_verified_legacy_period(self.con,point_id=8,farmer_id=1,
                starts_at=self.start,wallet_entry_id='paid',dry_run=False)
        self.assertEqual(self.con.execute('SELECT COUNT(*) FROM pickup_point_periods').fetchone()[0],1)
    def test_rejects_malformed_inputs_without_writing(self):
        for kwargs in (
            dict(point_id=True,farmer_id=1,starts_at=self.start,wallet_entry_id='paid'),
            dict(point_id=7,farmer_id=0,starts_at=self.start,wallet_entry_id='paid'),
            dict(point_id=7,farmer_id=1,starts_at='2026-11-18',wallet_entry_id='paid'),
            dict(point_id=7,farmer_id=1,starts_at=self.start,wallet_entry_id=''),
        ):
            with self.assertRaises(ValueError):
                import_verified_legacy_period(self.con,**kwargs,dry_run=False)
        self.assertEqual(self.con.execute('SELECT COUNT(*) FROM pickup_point_periods').fetchone()[0],0)
    def test_cannot_import_for_other_farmer(self):
        self.con.execute("INSERT INTO wallet_preview_entries VALUES('paid',2,'point_fee','charged',1000)")
        with self.assertRaises(ValueError):
            import_verified_legacy_period(self.con,point_id=7,farmer_id=2,
                starts_at=self.start,wallet_entry_id='paid',dry_run=False)

if __name__=='__main__':unittest.main()

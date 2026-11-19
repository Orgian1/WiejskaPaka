import sqlite3
import unittest
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from backend.pickup_point_periods import SCHEMA, period_end
from backend.pickup_point_legacy_audit import inspect_legacy_points

class LegacyPickupPointAuditTests(unittest.TestCase):
    def test_audit_is_read_only_and_does_not_grant_entitlements(self):
        con=sqlite3.connect(':memory:');con.row_factory=sqlite3.Row
        con.executescript('''CREATE TABLE users(id INTEGER PRIMARY KEY);
            CREATE TABLE pickup_points(id INTEGER PRIMARY KEY,farmer_id INTEGER,name TEXT,active INTEGER);
            INSERT INTO users VALUES(1);
            INSERT INTO pickup_points VALUES(10,1,'Legacy',1),(11,1,'Inactive',0),(12,1,'Promotional',1);''')
        con.executescript(SCHEMA)
        start=datetime(2026,11,18,12,tzinfo=ZoneInfo('Europe/Warsaw'))
        con.execute("INSERT INTO pickup_point_periods VALUES(?,?,?,?,?,0,'promotion',NULL)",
                    ('p',12,1,start.isoformat(),period_end(start).isoformat()))
        before=con.total_changes
        result=inspect_legacy_points(con,now=start+timedelta(days=1))
        self.assertEqual(result['active_without_entitlement'],1)
        self.assertEqual(result['active_with_entitlement'],1)
        self.assertEqual(result['inactive'],1)
        self.assertEqual(before,con.total_changes)
        self.assertEqual(con.execute('SELECT COUNT(*) FROM pickup_point_periods').fetchone()[0],1)
        con.close()

if __name__=='__main__':
    unittest.main()

import sqlite3
import unittest
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from backend.pickup_point_periods import SCHEMA, active_period, period_end, quote, point_status, entitled_point_ids

class PickupPointPeriodTests(unittest.TestCase):
    def test_public_listing_and_checkout_enforce_entitlement(self):
        from pathlib import Path
        source=Path('backend/app.py').read_text(encoding='utf-8')
        self.assertIn('eligible=entitled_point_ids(con',source)
        self.assertIn('active_period(con,payload.pickup_point_id) is None',source)

    def test_period_is_exactly_30_days(self):
        start=datetime(2026,11,18,12,0,tzinfo=ZoneInfo('Europe/Warsaw'))
        self.assertEqual(period_end(start)-start,timedelta(days=30))
        self.assertEqual(quote()['price_grosze'],1000)
        self.assertFalse(quote()['wallet_charge_available'])

    def test_daylight_saving_does_not_shorten_or_extend_paid_window(self):
        from datetime import timezone
        start=datetime(2027,3,20,12,0,tzinfo=ZoneInfo('Europe/Warsaw'))
        end=period_end(start)
        self.assertEqual(end.astimezone(timezone.utc)-start.astimezone(timezone.utc),timedelta(days=30))

    def test_promotion_does_not_create_wallet_charge(self):
        con=sqlite3.connect(':memory:');con.row_factory=sqlite3.Row
        con.executescript('CREATE TABLE users(id INTEGER PRIMARY KEY);CREATE TABLE pickup_points(id INTEGER PRIMARY KEY);')
        con.executescript(SCHEMA)
        start=datetime(2026,11,18,12,0,tzinfo=ZoneInfo('Europe/Warsaw'))
        end=period_end(start)
        con.execute('INSERT INTO pickup_point_periods VALUES(?,?,?,?,?,?,?,?)',
                    ('p',1,1,start.isoformat(),end.isoformat(),0,'promotion',None))
        self.assertEqual(active_period(con,1,now=start+timedelta(days=29))['kind'],'promotion')
        self.assertTrue(point_status(con,1,now=start+timedelta(days=29))['entitled'])
        self.assertEqual(entitled_point_ids(con,[1,2,1],now=start+timedelta(days=29)),{1})
        self.assertIsNone(active_period(con,1,now=end))
        self.assertFalse(point_status(con,1,now=end)['entitled'])
        self.assertEqual(entitled_point_ids(con,[1],now=end),set())
        with self.assertRaises(sqlite3.IntegrityError):
            con.execute('INSERT INTO pickup_point_periods VALUES(?,?,?,?,?,?,?,?)',
                        ('fake',2,1,start.isoformat(),end.isoformat(),1000,'wallet_test',None))
        con.close()

if __name__=='__main__':
    unittest.main()

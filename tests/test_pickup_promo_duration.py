"""Promotion code expiry and point activation expiry are independent."""
import sqlite3
import unittest
from datetime import date, datetime
from zoneinfo import ZoneInfo
from backend.pickup_promotions import SCHEMA, consume_for_point, point_terms


class PromoPointDurationTests(unittest.TestCase):
    def setUp(self):
        self.con=sqlite3.connect(':memory:')
        self.con.row_factory=sqlite3.Row
        self.con.execute('CREATE TABLE users(id INTEGER PRIMARY KEY)')
        self.con.execute('CREATE TABLE pickup_points(id INTEGER PRIMARY KEY)')
        self.con.executescript(SCHEMA)
        self.con.execute('INSERT INTO users VALUES (1)')
        self.con.execute('INSERT INTO pickup_points VALUES (11),(12)')
        self.con.execute("INSERT INTO pickup_promo_codes VALUES ('TEST','2027-12-31',10,1,1)")
        self.con.execute("INSERT INTO pickup_promo_grants VALUES ('g',1,'TEST','2027-12-31',2)")

    def tearDown(self):
        self.con.close()

    def test_each_point_has_own_thirty_day_window(self):
        first=consume_for_point(self.con,1,11,today=date(2026,11,18))
        second=consume_for_point(self.con,1,12,today=date(2026,11,20))
        self.assertTrue(first['free_until'].startswith('2026-12-18'))
        self.assertTrue(second['free_until'].startswith('2026-12-20'))
        self.assertEqual(point_terms(self.con,11)['free_until'],first['free_until'])
        self.assertNotEqual(first['free_until'],'2027-12-31')
        self.assertFalse(first['charges_executed'])


if __name__=='__main__':
    unittest.main()

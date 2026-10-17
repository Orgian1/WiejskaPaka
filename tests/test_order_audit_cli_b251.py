import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.run_order_audit import run, main, save_atomic


class AuditCliTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.db = self.base / 'test.sqlite3'
        with sqlite3.connect(self.db) as c:
            c.executescript('''CREATE TABLE orders(id INTEGER,product_id INTEGER,farmer_id INTEGER,quantity INTEGER,subtotal_grosze INTEGER,delivery_grosze INTEGER,total_grosze INTEGER,fulfillment TEXT,status TEXT,pin_used INTEGER,confirmed_at TEXT);
            CREATE TABLE products(id INTEGER,farmer_id INTEGER,stock INTEGER);
            CREATE TABLE order_locations(order_id INTEGER,pickup_point_id INTEGER,delivery_city TEXT,delivery_street TEXT,delivery_postal_code TEXT);
            INSERT INTO products VALUES(1,2,3);
            INSERT INTO orders VALUES(1,1,2,1,1000,0,1000,'odbior','oczekuje_na_platnosc_testowa',0,NULL);
            INSERT INTO order_locations VALUES(1,4,NULL,NULL,NULL);''')

    def test_clean_database(self):
        self.assertTrue(run(self.db)['ok'])

    def test_detects_problem_and_exit_code(self):
        with sqlite3.connect(self.db) as c:
            c.execute('UPDATE orders SET total_grosze=900 WHERE id=1')
        self.assertEqual(main(['--database', str(self.db)]), 1)
        self.assertEqual(run(self.db)['issues'][0]['code'], 'ORDER_TOTAL_MISMATCH')

    def test_missing_database_does_not_create(self):
        missing = self.base / 'missing.db'
        self.assertEqual(main(['--database', str(missing)]), 2)
        self.assertFalse(missing.exists())

    def test_report_atomic(self):
        report = self.base / 'report.json'
        self.assertEqual(main(['--database', str(self.db), '--report', str(report)]), 0)
        self.assertEqual(json.loads(report.read_text())['checked_orders'], 1)

    def test_database_remains_unchanged(self):
        before = self.db.read_bytes()
        run(self.db)
        self.assertEqual(self.db.read_bytes(), before)

    def test_no_personal_data_in_report(self):
        result = run(self.db)
        self.assertEqual(set(result), {'checked_orders', 'checked_products', 'issues', 'ok'})


if __name__ == '__main__':
    unittest.main()

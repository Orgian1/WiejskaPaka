import sqlite3
import unittest
from backend.order_integrity import audit_orders


class OrderIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(':memory:')
        self.db.row_factory = sqlite3.Row
        self.db.executescript('''
            CREATE TABLE products(id INTEGER, farmer_id INTEGER, stock INTEGER);
            CREATE TABLE orders(id INTEGER, product_id INTEGER, farmer_id INTEGER,
              quantity INTEGER, subtotal_grosze INTEGER, delivery_grosze INTEGER,
              total_grosze INTEGER, fulfillment TEXT, status TEXT, pin_used INTEGER,
              confirmed_at TEXT);
            CREATE TABLE order_locations(order_id INTEGER, pickup_point_id INTEGER,
              delivery_city TEXT, delivery_street TEXT, delivery_postal_code TEXT);
            INSERT INTO products VALUES(1, 10, 5);
            INSERT INTO orders VALUES(1,1,10,2,1001,0,1001,'odbior','odebrane',1,'2026-10-15');
            INSERT INTO order_locations VALUES(1,3,NULL,NULL,NULL);
        ''')

    def tearDown(self):
        self.db.close()

    def codes(self):
        return {i['code'] for i in audit_orders(self.db)['issues']}

    def test_valid(self):
        self.assertTrue(audit_orders(self.db)['ok'])

    def test_mismatched_seller(self):
        self.db.execute('UPDATE products SET farmer_id=11')
        self.assertIn('PRODUCT_SELLER_MISMATCH', self.codes())

    def test_amount_mismatch(self):
        self.db.execute('UPDATE orders SET total_grosze=999')
        self.assertIn('ORDER_TOTAL_MISMATCH', self.codes())

    def test_missing_location(self):
        self.db.execute('DELETE FROM order_locations')
        self.assertIn('MISSING_LOCATION', self.codes())

    def test_confirmation(self):
        self.db.execute('UPDATE orders SET pin_used=0')
        self.assertIn('CONFIRMATION_INCONSISTENT', self.codes())

    def test_pin_without_receipt(self):
        self.db.execute("UPDATE orders SET status='nowe'")
        self.assertIn('PIN_USED_WITHOUT_RECEIPT', self.codes())

    def test_invalid_stock(self):
        self.db.execute('UPDATE products SET stock=-1')
        self.assertIn('INVALID_STOCK', self.codes())

    def test_delivery_mismatch(self):
        self.db.execute("UPDATE orders SET fulfillment='dostawa'")
        self.assertIn('DELIVERY_LOCATION_MISMATCH', self.codes())

    def test_missing_product(self):
        self.db.execute('DELETE FROM products')
        self.assertIn('MISSING_PRODUCT', self.codes())


if __name__ == '__main__':
    unittest.main()

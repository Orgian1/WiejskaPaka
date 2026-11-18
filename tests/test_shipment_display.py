"""Readable shipment reference tests with disposable SQLite database."""
import sqlite3
import unittest
from backend.shipment_display import display_shipment_number


class ShipmentDisplayTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        self.db.row_factory = sqlite3.Row
        self.db.executescript("""
          CREATE TABLE pickup_points(id INTEGER PRIMARY KEY, farmer_id INTEGER);
          CREATE TABLE shipment_groups(id TEXT PRIMARY KEY,farmer_id INTEGER,fulfillment TEXT,created_at TEXT);
          CREATE TABLE shipment_order_links(order_id INTEGER,shipment_id TEXT);
          CREATE TABLE order_locations(order_id INTEGER,pickup_point_id INTEGER);
          INSERT INTO pickup_points VALUES (10,7),(20,7),(30,8);
          INSERT INTO shipment_groups VALUES
            ('WPS-one',7,'odbior','2026-11-18T10:00:00'),
            ('WPS-two',7,'odbior','2026-11-18T11:00:00'),
            ('WPS-three',7,'odbior','2026-11-18T12:00:00'),
            ('WPS-four',7,'dostawa','2026-11-18T13:00:00');
          INSERT INTO shipment_order_links VALUES
            (1,'WPS-one'),(2,'WPS-one'),(3,'WPS-two'),(4,'WPS-three');
          INSERT INTO order_locations VALUES (1,10),(2,10),(3,10),(4,20);
        """)

    def tearDown(self):
        self.db.close()

    def test_counts_shipments_not_products(self):
        self.assertEqual(display_shipment_number(self.db,7,10,'WPS-one','298834'),'A001-298')
        self.assertEqual(display_shipment_number(self.db,7,10,'WPS-two','123456'),'A002-123')
        self.assertEqual(display_shipment_number(self.db,7,20,'WPS-three','000999'),'B001-000')

    def test_delivery_has_separate_prefix(self):
        self.assertEqual(display_shipment_number(self.db,7,None,'WPS-four','987654'),'D001-987')

    def test_pin_validation(self):
        with self.assertRaises(ValueError):
            display_shipment_number(self.db,7,10,'WPS-one','123')

    def test_persisted_reference_contract(self):
        from pathlib import Path
        root = Path(__file__).resolve().parents[1]
        backend = (root/'backend'/'app.py').read_text(encoding='utf-8')
        frontend = (root/'web'/'app-views.js').read_text(encoding='utf-8')
        migration = (root/'database'/'upgrade_shipment_public_refs.sql').read_text(encoding='utf-8')
        self.assertIn('INSERT INTO shipment_public_refs(shipment_id,farmer_id,public_number)', backend)
        self.assertIn('AS display_shipment_number', backend)
        self.assertIn("orderShipmentPublicRefs.set(String(order.id),order.display_shipment_number)", frontend)
        self.assertIn('CREATE TABLE IF NOT EXISTS shipment_public_refs', migration)

    def test_frontend_keeps_internal_id(self):
        from pathlib import Path
        source=(Path(__file__).resolve().parents[1]/'web'/'app-views.js').read_text(encoding='utf-8')
        self.assertIn("displayShipmentRefs.set(result.shipment_id,result.display_shipment_number)",source)
        self.assertIn("current.replace(technical,visible)",source)


if __name__=='__main__':
    unittest.main()

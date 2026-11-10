"""Sale-unit metadata kept separate from legacy integer stock/quantity.

These records describe ONE existing sales quantity, not grams. Fractional sales
must use a future versioned quantity contract; do not reinterpret legacy stock.
Call insert_product_unit only in the transaction creating a new listing.
"""
import json

from backend.product_units import get_unit, package_content

SCHEMA_SQLITE = '''
CREATE TABLE IF NOT EXISTS product_sale_units (
 product_id INTEGER PRIMARY KEY REFERENCES products(id) ON DELETE CASCADE,
 unit TEXT NOT NULL CHECK(unit IN ('szt','kg','g','l','ml','opak','peczek','sloik','butelka','worek','skrzynka','tacka')),
 content_json TEXT
);
CREATE TRIGGER IF NOT EXISTS product_sale_units_immutable BEFORE UPDATE ON product_sale_units
BEGIN SELECT RAISE(ABORT,'Sale units cannot be changed'); END;
CREATE TRIGGER IF NOT EXISTS product_sale_units_no_replace BEFORE INSERT ON product_sale_units
WHEN EXISTS(SELECT 1 FROM product_sale_units WHERE product_id=NEW.product_id)
BEGIN SELECT RAISE(ABORT,'Sale units cannot be replaced'); END;
CREATE TRIGGER IF NOT EXISTS product_sale_units_no_delete BEFORE DELETE ON product_sale_units
BEGIN SELECT RAISE(ABORT,'Sale units cannot be removed'); END;
CREATE TABLE IF NOT EXISTS order_sale_units (
 order_id INTEGER PRIMARY KEY REFERENCES orders(id),
 unit TEXT NOT NULL CHECK(unit IN ('szt','kg','g','l','ml','opak','peczek','sloik','butelka','worek','skrzynka','tacka')),
 content_json TEXT
);
CREATE TRIGGER IF NOT EXISTS order_sale_units_immutable_update BEFORE UPDATE ON order_sale_units
BEGIN SELECT RAISE(ABORT,'Order sale units are insert-only'); END;
CREATE TRIGGER IF NOT EXISTS order_sale_units_immutable_delete BEFORE DELETE ON order_sale_units
BEGIN SELECT RAISE(ABORT,'Order sale units are insert-only'); END;
CREATE TRIGGER IF NOT EXISTS order_sale_units_no_replace BEFORE INSERT ON order_sale_units
WHEN EXISTS(SELECT 1 FROM order_sale_units WHERE order_id=NEW.order_id)
BEGIN SELECT RAISE(ABORT,'Order sale units cannot be replaced'); END;
'''


def insert_product_unit(con, product_id, code, amount=None, content_unit=None):
    get_unit(code)
    content = package_content(code, amount, content_unit)
    # Never retroactively label a listing already used in a cart or order.
    if con.execute('SELECT id FROM orders WHERE product_id=? LIMIT 1', (product_id,)).fetchone():
        raise ValueError('Nie można zmienić jednostki zamówionego produktu')
    if con.execute('SELECT product_id FROM saved_cart_items WHERE product_id=? LIMIT 1', (product_id,)).fetchone():
        raise ValueError('Nie można zmienić jednostki produktu w koszyku')
    con.execute('INSERT INTO product_sale_units(product_id,unit,content_json) VALUES(?,?,?)',
                (product_id, code, json.dumps(content, separators=(',', ':')) if content else None))


def product_unit(con, product_id):
    row = con.execute('SELECT unit,content_json FROM product_sale_units WHERE product_id=?', (product_id,)).fetchone()
    if row is None:
        return {'sale_unit': 'szt', 'package_content': None}
    return {'sale_unit': row['unit'], 'package_content': json.loads(row['content_json']) if row['content_json'] else None}


def capture_order_unit(con, order_id):
    """Snapshot within checkout transaction. Never backfill historical orders."""
    order = con.execute('SELECT product_id FROM orders WHERE id=?', (order_id,)).fetchone()
    if order is None:
        raise ValueError('Nie znaleziono zamówienia')
    details = product_unit(con, order['product_id'])
    content = details['package_content']
    con.execute('INSERT INTO order_sale_units(order_id,unit,content_json) VALUES(?,?,?)',
                (order_id, details['sale_unit'], json.dumps(content, separators=(',', ':')) if content else None))


def enabled():
    import os
    return os.environ.get('WP_ENABLE_PRODUCT_UNITS') == '1'


def enrich_product(con, row):
    result = dict(row)
    if enabled():
        result.update(product_unit(con, result.get('product_id', result.get('id'))))
    return result

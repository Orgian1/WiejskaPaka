import sqlite3
from backend.order_integrity import audit_orders


def fixture(status='oczekuje_na_platnosc_testowa', fulfillment='odbior', pin_used=0, confirmed_at=None):
    con = sqlite3.connect(':memory:')
    con.row_factory = sqlite3.Row
    con.executescript('''
      CREATE TABLE products(id INTEGER, farmer_id INTEGER, stock INTEGER);
      CREATE TABLE orders(id INTEGER, product_id INTEGER, farmer_id INTEGER, quantity INTEGER,
        subtotal_grosze INTEGER, delivery_grosze INTEGER, total_grosze INTEGER,
        fulfillment TEXT, status TEXT, pin_used INTEGER, confirmed_at TEXT);
      CREATE TABLE order_locations(order_id INTEGER, pickup_point_id INTEGER,
        delivery_city TEXT, delivery_street TEXT, delivery_postal_code TEXT);
      INSERT INTO products VALUES(2, 4, 5);
      INSERT INTO order_locations VALUES(1, 7, NULL, NULL, NULL);
    ''')
    con.execute('INSERT INTO orders VALUES(1,2,4,1,101,0,101,?,?,?,?)',
                (fulfillment, status, pin_used, confirmed_at))
    return con


def codes(con):
    return {i['code'] for i in audit_orders(con)['issues']}


def test_valid_pending_order():
    assert not codes(fixture())


def test_unknown_status():
    assert 'UNKNOWN_ORDER_STATUS' in codes(fixture(status='arbitrary'))


def test_delivery_status_not_allowed_for_pickup():
    assert 'STATUS_FULFILLMENT_MISMATCH' in codes(fixture(status='w_drodze_testowo'))


def test_pickup_status_not_allowed_for_delivery():
    assert 'STATUS_FULFILLMENT_MISMATCH' in codes(fixture(status='gotowe_do_odbioru_testowo', fulfillment='dostawa'))


def test_confirmation_timestamp_without_receipt():
    assert 'CONFIRMED_TIMESTAMP_WITHOUT_RECEIPT' in codes(fixture(confirmed_at='2026-10-15'))


def test_pin_used_without_receipt():
    assert 'PIN_USED_WITHOUT_RECEIPT' in codes(fixture(pin_used=1))


def test_completed_order_with_pin_and_timestamp():
    assert not codes(fixture(status='odebrane', pin_used=1, confirmed_at='2026-10-15'))

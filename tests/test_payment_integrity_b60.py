import sqlite3
from backend.payment_integrity import audit_payment_integrity


def make_db():
    con = sqlite3.connect(':memory:')
    con.row_factory = sqlite3.Row
    con.executescript('''
        CREATE TABLE orders(id INTEGER PRIMARY KEY, subtotal_grosze INTEGER,
            delivery_grosze INTEGER, total_grosze INTEGER, status TEXT);
        CREATE TABLE payment_simulations(order_id INTEGER PRIMARY KEY, total_grosze INTEGER,
            products_grosze INTEGER, delivery_grosze INTEGER, commission_grosze INTEGER,
            seller_grosze INTEGER, state TEXT, refund_grosze INTEGER, payout_grosze INTEGER);
        CREATE TABLE payment_simulation_events(event_id TEXT, order_id INTEGER);
        INSERT INTO orders VALUES(1,349,501,850,'nieudana_dostawa_testowo');
        INSERT INTO payment_simulations VALUES(1,850,349,501,17,833,'refunded_test',850,0);
    ''')
    return con


def test_b56_valid_full_refund():
    with make_db() as con:
        assert audit_payment_integrity(con) == {'checked_payments': 1, 'issues': [], 'ok': True}


def test_b57_refund_and_payout_detected():
    with make_db() as con:
        con.execute('UPDATE payment_simulations SET payout_grosze=1 WHERE order_id=1')
        codes = {issue['code'] for issue in audit_payment_integrity(con)['issues']}
        assert 'REFUND_AND_PAYOUT' in codes


def test_b58_order_amount_mismatch_detected():
    with make_db() as con:
        con.execute('UPDATE orders SET total_grosze=851 WHERE id=1')
        assert 'TOTAL_MISMATCH' in {x['code'] for x in audit_payment_integrity(con)['issues']}


def test_b59_incomplete_refund_and_wrong_status_detected():
    with make_db() as con:
        con.execute("UPDATE orders SET status='odebrane' WHERE id=1")
        con.execute('UPDATE payment_simulations SET refund_grosze=849 WHERE order_id=1')
        codes = {x['code'] for x in audit_payment_integrity(con)['issues']}
        assert {'INCOMPLETE_REFUND', 'REFUND_ORDER_STATUS_MISMATCH'} <= codes


def test_b60_orphan_event_detected():
    with make_db() as con:
        con.execute("INSERT INTO payment_simulation_events VALUES('ev1', 999)")
        assert 'ORPHAN_EVENT' in {x['code'] for x in audit_payment_integrity(con)['issues']}

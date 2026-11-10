import sqlite3
from backend.payment_integrity import audit_payment_integrity
from backend.payment_store import SCHEMA_SQLITE, create_payment, persist_event


def make_db():
    con = sqlite3.connect(':memory:')
    con.row_factory = sqlite3.Row
    con.executescript('''
        CREATE TABLE orders(id INTEGER PRIMARY KEY, subtotal_grosze INTEGER,
            delivery_grosze INTEGER, total_grosze INTEGER, status TEXT,
            fulfillment TEXT, buyer_id INTEGER, farmer_id INTEGER);
        CREATE TABLE order_events(order_id INTEGER,actor_id INTEGER,event_type TEXT,
            previous_status TEXT,new_status TEXT);
        CREATE TABLE shipment_order_links(order_id INTEGER,shipment_id TEXT);
        INSERT INTO orders VALUES(1,349,501,850,'nieudana_dostawa_testowo','dostawa',2,3);
        INSERT INTO order_events VALUES(1,3,'courier_delivery_failed_test',
            'w_drodze_testowo','nieudana_dostawa_testowo');
    ''' + SCHEMA_SQLITE)
    payment = create_payment(con, {'id': 1, 'subtotal_grosze': 349, 'delivery_grosze': 501, 'total_grosze': 850})
    payment = persist_event(con, payment, 'paid', 'payment_success_test', 'now')
    persist_event(con, payment, 'refund', 'delivery_failed_by_courier_test', 'now')
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
        con.execute("INSERT INTO payment_simulation_events VALUES('ev1',999,'payment_success_test','paid_test','now')")
        assert 'ORPHAN_EVENT' in {x['code'] for x in audit_payment_integrity(con)['issues']}

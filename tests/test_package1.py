import sqlite3
import pytest
from backend.psp_reconciliation import reconcile_test_payments


def setup():
    con = sqlite3.connect(':memory:')
    con.row_factory = sqlite3.Row
    con.execute('CREATE TABLE payment_simulations(order_id INTEGER PRIMARY KEY,total_grosze INTEGER,refund_grosze INTEGER,state TEXT)')
    con.executemany('INSERT INTO payment_simulations VALUES(?,?,?,?)', [
        (1, 1199, 0, 'completed_test'), (2, 2000, 2000, 'refunded_test'),
        (3, 500, 0, 'pending_test')])
    return con


def test_matching_and_discrepancies():
    result = reconcile_test_payments(setup(), [
        {'order_id': 1, 'amount_grosze': 1199, 'status': 'paid'},
        {'order_id': 2, 'amount_grosze': 2000, 'status': 'refunded'},
        {'order_id': 3, 'amount_grosze': 501, 'status': 'paid'},
        {'order_id': 9, 'amount_grosze': 100, 'status': 'paid'}])
    assert (result['matched'], result['mismatched'], result['unknown_orders']) == (2, 1, 1)
    assert len(result['items'][2]['reasons']) == 2


@pytest.mark.parametrize('rows', [
    [{'order_id': 1, 'amount_grosze': 1.0, 'status': 'paid'}],
    [{'order_id': True, 'amount_grosze': 1, 'status': 'paid'}],
    [{'order_id': 1, 'amount_grosze': -1, 'status': 'paid'}],
    [{'order_id': 1, 'amount_grosze': 1, 'status': 'success'}],
    [{'order_id': 1, 'amount_grosze': 1, 'status': 'paid', 'iban': 'x'}],
    [{'order_id': 1, 'amount_grosze': 1, 'status': 'paid'}] * 2,
    [{'order_id': 1, 'amount_grosze': 1, 'status': 'paid'}] * 501,
])
def test_rejects_invalid_data(rows):
    with pytest.raises(ValueError):
        reconcile_test_payments(setup(), rows)


def test_read_only():
    con = setup()
    reconcile_test_payments(con, [{'order_id': 1, 'amount_grosze': 0, 'status': 'pending'}])
    assert con.execute('SELECT total_grosze FROM payment_simulations WHERE order_id=1').fetchone()[0] == 1199

from tests.test_stage23 import setup
from backend.payout_batches import create_plan
from backend.payout_reconciliation import reconcile_plan


def prepare():
    con = setup()
    con.execute('ALTER TABLE orders ADD COLUMN status TEXT')
    con.execute("UPDATE orders SET status='odebrane' WHERE id IN (1,3)")
    create_plan(con, 1, '2026-10-19', 'now')
    return con


def test_eligible_snapshot():
    con = prepare()
    result = reconcile_plan(con, 1, '2026-10-19')
    assert result['status'] == 'verified_test'
    assert result['eligible_seller_grosze'] == 96
    assert not result['transfer_executed']


def test_refund_or_payment_change_blocks():
    con = prepare()
    con.execute("UPDATE payment_simulations SET state='refunded_test', refund_grosze=101 WHERE order_id=1")
    result = reconcile_plan(con, 1, '2026-10-19')
    assert result['status'] == 'blocked_test'
    assert 'refund_recorded' in result['checks'][0]['problems']
    assert result['eligible_seller_grosze'] == 0


def test_status_change_blocks():
    con = prepare()
    con.execute("UPDATE orders SET status='anulowane' WHERE id=1")
    assert 'order_not_collected' in reconcile_plan(con,1,'2026-10-19')['checks'][0]['problems']


def test_paid_or_amount_change_blocks():
    con = prepare()
    con.execute('UPDATE payment_simulations SET payout_grosze=96, seller_grosze=95, commission_grosze=6 WHERE order_id=1')
    problems = reconcile_plan(con,1,'2026-10-19')['checks'][0]['problems']
    assert 'already_paid_test' in problems and 'amount_changed' in problems


def test_isolation_and_missing():
    con = prepare()
    assert reconcile_plan(con,2,'2026-10-19') is None
    assert reconcile_plan(con,1,'2026-10-26') is None

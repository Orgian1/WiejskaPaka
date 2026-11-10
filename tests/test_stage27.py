from tests.test_stage25 import ready
from backend.payout_reservations import reserve_plan
from backend.payout_auto_review import invalidate_stale_reservations


def test_auto_cancels_refunded_reservation_and_is_idempotent():
    con = ready()
    reserve_plan(con, 1, '2026-10-19', 'now')
    assert invalidate_stale_reservations(con, 1)['cancelled_count'] == 0
    con.execute('UPDATE payment_simulations SET refund_grosze=101 WHERE order_id=1')
    result = invalidate_stale_reservations(con, 1)
    assert result['checked'] == 1
    assert result['cancelled_count'] == 1
    assert result['transfer_executed'] is False
    assert invalidate_stale_reservations(con, 1)['checked'] == 0
    assert con.execute('SELECT status FROM payout_reservations').fetchone()[0] == 'cancelled_test'
    assert con.execute('SELECT COUNT(*) FROM payout_reservation_items').fetchone()[0] == 1


def test_auto_review_isolated_by_farmer():
    con = ready()
    reserve_plan(con, 1, '2026-10-19', 'now')
    assert invalidate_stale_reservations(con, 2)['checked'] == 0
    assert con.execute('SELECT status FROM payout_reservations').fetchone()[0] == 'reserved_test'

import pytest
from tests.test_stage25 import ready
from backend.payout_reservations import reserve_plan
from backend.payout_reservation_review import review_reservation,cancel_reservation


def test_review_detects_refund_after_reservation():
    con=ready()
    reserve_plan(con,1,'2026-10-19','now')
    assert review_reservation(con,1,'2026-10-19')['valid_test']
    con.execute('UPDATE payment_simulations SET refund_grosze=101 WHERE order_id=1')
    assert not review_reservation(con,1,'2026-10-19')['valid_test']


def test_cancel_idempotent_and_cannot_reserve_again():
    con=ready()
    reserve_plan(con,1,'2026-10-19','now')
    first=cancel_reservation(con,1,'2026-10-19')
    assert first == cancel_reservation(con,1,'2026-10-19')
    assert not first['valid_test']
    with pytest.raises(ValueError):
        reserve_plan(con,1,'2026-10-19','later')
    assert con.execute('SELECT COUNT(*) FROM payout_reservation_items').fetchone()[0]==1


def test_isolation_and_missing_reservation():
    con=ready()
    reserve_plan(con,1,'2026-10-19','now')
    assert review_reservation(con,2,'2026-10-19') is None
    with pytest.raises(ValueError):
        cancel_reservation(con,2,'2026-10-19')

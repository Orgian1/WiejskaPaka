import pytest
from tests.test_stage24 import prepare
from backend.payout_reservations import SCHEMA_SQLITE, reserve_plan


def ready():
    con=prepare()
    con.executescript(SCHEMA_SQLITE)
    return con


def test_reserve_once_and_no_transfer():
    con=ready()
    a=reserve_plan(con,1,'2026-10-19','now')
    assert a['amount_grosze']==96 and not a['transfer_executed']
    assert reserve_plan(con,1,'2026-10-19','later')==a
    assert con.execute('SELECT COUNT(*) FROM payout_reservation_items').fetchone()[0]==1


def test_block_refunded_plan():
    con=ready()
    con.execute("UPDATE payment_simulations SET refund_grosze=101 WHERE order_id=1")
    with pytest.raises(ValueError):
        reserve_plan(con,1,'2026-10-19','now')
    assert con.execute('SELECT COUNT(*) FROM payout_reservations').fetchone()[0]==0


def test_other_farmer_and_missing_plan():
    con=ready()
    with pytest.raises(ValueError):
        reserve_plan(con,2,'2026-10-19','now')
    with pytest.raises(ValueError):
        reserve_plan(con,1,'2026-10-26','now')


def test_amount_change_blocks():
    con=ready()
    con.execute('UPDATE payment_simulations SET seller_grosze=95, commission_grosze=6 WHERE order_id=1')
    with pytest.raises(ValueError):
        reserve_plan(con,1,'2026-10-19','now')

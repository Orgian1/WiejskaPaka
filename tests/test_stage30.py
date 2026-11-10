import sqlite3
import pytest
from backend.payment_store import SCHEMA_SQLITE
from backend.platform_reports import monthly_platform_report, validate_month


def setup():
    con = sqlite3.connect(':memory:')
    con.row_factory = sqlite3.Row
    con.executescript('CREATE TABLE orders(id INTEGER PRIMARY KEY);' + SCHEMA_SQLITE)
    con.executemany('INSERT INTO orders(id) VALUES(?)', [(1,), (2,), (3,)])
    for i in (1, 2, 3):
        state = 'refunded_test' if i == 2 else 'completed_test'
        con.execute('''INSERT INTO payment_simulations
          (order_id,total_grosze,products_grosze,delivery_grosze,commission_grosze,seller_grosze,state,refund_grosze)
          VALUES(?,1200,1000,200,50,1150,?,?)''', (i, state, 1200 if i == 2 else 0))
    for order_id, event_id, event_type, state_after, created_at in [
        (1,'a','order_completed_test','completed_test','2026-10-04T12:00:00Z'),
        (1,'b','weekly_payout_test','paid_out_test','2026-10-05T12:00:00Z'),
        (2,'c','order_completed_test','completed_test','2026-10-04T12:00:00Z'),
        (2,'d','delivery_failed_by_courier_test','refunded_test','2026-10-06T12:00:00Z'),
        (3,'e','order_completed_test','completed_test','2026-09-30T12:00:00Z')]:
        con.execute('INSERT INTO payment_simulation_events VALUES(?,?,?,?,?)',
                    (event_id,order_id,event_type,state_after,created_at))
    return con


def test_monthly_excludes_refunded_and_other_month():
    con = setup()
    result = monthly_platform_report(con,'2026-10')
    assert result['eligible_order_count'] == 1
    assert result['platform_commission_grosze'] == 50
    assert result['gross_order_grosze'] == 1200
    assert result['seller_due_grosze'] == 1150
    assert result['refund_event_order_count'] == 1
    assert result['report_type'].startswith('test_')


def test_monthly_empty():
    assert monthly_platform_report(setup(),'2026-08')['gross_order_grosze'] == 0


@pytest.mark.parametrize('month', ['2026-00','2026-13','2026-1','2026-10 OR 1=1','bad'])
def test_bad_month(month):
    with pytest.raises(ValueError):
        validate_month(month)

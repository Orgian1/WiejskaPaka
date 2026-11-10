import sqlite3
from datetime import date
from backend.payment_store import SCHEMA_SQLITE
from backend.payout_reports import summarize, seller_report, next_weekly_date


def test_balances_only_completed_and_paid():
    rows = [dict(state=s, seller_grosze=101, commission_grosze=5, payout_grosze=p)
            for s,p in [('completed_test',0),('paid_out_test',101),('refunded_test',0),('paid_test',0)]]
    result = summarize(rows)
    assert result['pending_grosze'] == 101
    assert result['paid_out_grosze'] == 101
    assert result['platform_commission_earned_grosze'] == 10
    assert result['eligible_orders'] == 1 and result['paid_orders'] == 1


def test_report_isolated_by_seller():
    con = sqlite3.connect(':memory:')
    con.row_factory = sqlite3.Row
    con.executescript('CREATE TABLE orders(id INTEGER PRIMARY KEY, farmer_id INTEGER NOT NULL);' + SCHEMA_SQLITE)
    con.executemany('INSERT INTO orders VALUES(?,?)', [(1,11),(2,22)])
    for i in (1,2):
        con.execute('''INSERT INTO payment_simulations
            (order_id,total_grosze,products_grosze,delivery_grosze,commission_grosze,seller_grosze,state)
            VALUES(?,100,100,0,5,95,'completed_test')''', (i,))
    report = seller_report(con,11)
    assert report['eligible_grosze'] == 95
    assert [o['order_id'] for o in report['orders']] == [1]
    con.close()


def test_weekly_monday_date():
    assert next_weekly_date(date(2026,10,14)) == date(2026,10,19)
    assert next_weekly_date(date(2026,10,19)) == date(2026,10,19)

import sqlite3
from backend.payment_store import SCHEMA_SQLITE as PAYMENTS
from backend.payout_batches import SCHEMA_SQLITE, create_plan, get_plan


def setup():
    con=sqlite3.connect(':memory:')
    con.row_factory=sqlite3.Row
    con.execute('PRAGMA foreign_keys=ON')
    con.executescript('CREATE TABLE users(id INTEGER PRIMARY KEY); CREATE TABLE orders(id INTEGER PRIMARY KEY,farmer_id INTEGER);'+PAYMENTS+SCHEMA_SQLITE)
    con.executemany('INSERT INTO users(id) VALUES(?)',[(1,),(2,)])
    con.executemany('INSERT INTO orders(id,farmer_id) VALUES(?,?)',[(1,1),(2,1),(3,2)])
    for i,state in [(1,'completed_test'),(2,'paid_test'),(3,'completed_test')]:
        con.execute('''INSERT INTO payment_simulations(order_id,total_grosze,products_grosze,delivery_grosze,commission_grosze,seller_grosze,state)
           VALUES(?,101,101,0,5,96,?)''',(i,state))
    return con


def test_plans_are_isolated_and_idempotent():
    con=setup()
    first=create_plan(con,1,'2026-10-19','now')
    again=create_plan(con,1,'2026-10-19','later')
    assert first==again and first['seller_total_grosze']==96
    assert [i['order_id'] for i in first['items']]==[1]
    assert get_plan(con,2,'2026-10-19') is None
    assert con.execute('SELECT COUNT(*) FROM payout_plan_items').fetchone()[0]==1


def test_no_duplicate_order_across_weeks():
    con=setup()
    create_plan(con,1,'2026-10-19','now')
    next_plan=create_plan(con,1,'2026-10-26','now')
    assert next_plan['status']=='nothing_to_plan_test'
    assert con.execute('SELECT COUNT(*) FROM payout_plan_items').fetchone()[0]==1


def test_other_farmer_has_separate_plan():
    con=setup()
    plan=create_plan(con,2,'2026-10-19','now')
    assert [i['order_id'] for i in plan['items']]==[3]


def test_only_mondays_allowed():
    import pytest
    con=setup()
    with pytest.raises(ValueError):
        create_plan(con,1,'2026-10-20','now')

import sqlite3
import pytest
from backend.payment_store import SCHEMA_SQLITE, create_payment, get_payment, persist_event

@pytest.fixture
def con():
    db = sqlite3.connect(':memory:')
    db.row_factory = sqlite3.Row
    db.executescript('CREATE TABLE orders(id INTEGER PRIMARY KEY);' + SCHEMA_SQLITE)
    db.execute('INSERT INTO orders(id) VALUES(1)')
    yield db
    db.close()

ORDER = {'id':1,'subtotal_grosze':9999,'delivery_grosze':1200,'total_grosze':11199}

def test_persists_across_reads(con):
    payment = create_payment(con, ORDER)
    updated = persist_event(con,payment,'event-1','payment_success_test','2026-10-14T00:00:00Z')
    assert updated.state == get_payment(con,1).state == 'paid_test'
    assert len(get_payment(con,1).processed_event_ids) == 1

def test_duplicate_event_idempotent(con):
    p = create_payment(con,ORDER)
    p = persist_event(con,p,'evt','payment_success_test','now')
    p = persist_event(con,p,'evt','payment_success_test','later')
    assert con.execute('SELECT COUNT(*) FROM payment_simulation_events').fetchone()[0] == 1
    with pytest.raises(ValueError):
        persist_event(con,p,'evt','payment_failed_test','later')

def test_full_refund_persisted(con):
    p = create_payment(con,ORDER)
    p = persist_event(con,p,'paid','payment_success_test','now')
    p = persist_event(con,p,'refund','delivery_failed_by_courier_test','now')
    assert get_payment(con,1).refund_grosze == 11199
    assert get_payment(con,1).payout_grosze == 0

def test_no_double_payout(con):
    p = create_payment(con,ORDER)
    p = persist_event(con,p,'paid','payment_success_test','now')
    p = persist_event(con,p,'complete','order_completed_test','now')
    p = persist_event(con,p,'payout','weekly_payout_test','now')
    assert p.payout_grosze == 10699
    with pytest.raises(ValueError):
        persist_event(con,p,'another-payout','weekly_payout_test','now')

def test_inconsistent_order_rejected(con):
    with pytest.raises(ValueError):
        create_payment(con,{**ORDER,'total_grosze':11198})

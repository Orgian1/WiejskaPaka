import sqlite3
import pytest
from backend.seller_compliance import create_compliance_tables, seller_compliance_status, acknowledge_seller_rules, review_seller_account

@pytest.fixture
def con():
    c=sqlite3.connect(':memory:')
    c.row_factory=sqlite3.Row
    c.execute('PRAGMA foreign_keys=ON')
    c.executescript('''CREATE TABLE users(id INTEGER PRIMARY KEY,role TEXT);
    CREATE TABLE orders(id INTEGER PRIMARY KEY,farmer_id INTEGER,status TEXT,buyer_id INTEGER);
    CREATE TABLE shipment_groups(id TEXT PRIMARY KEY,farmer_id INTEGER,buyer_id INTEGER);
    CREATE TABLE shipment_order_links(order_id INTEGER PRIMARY KEY,shipment_id TEXT);
    INSERT INTO users VALUES(1,'rolnik'),(2,'admin');
    INSERT INTO orders VALUES(1,1,'potwierdzone',3);''')
    create_compliance_tables(c)
    yield c
    c.close()

def test_status_before_ack(con):
    status=seller_compliance_status(con,1)
    assert status['review_status']=='not_started'
    assert status['order_count_observed']==1
    assert not status['can_receive_real_payouts']

def test_ack_idempotent(con):
    acknowledge_seller_rules(con,1,'2026-10-draft')
    acknowledge_seller_rules(con,1,'2026-10-draft')
    assert con.execute('SELECT COUNT(*) FROM seller_compliance_events').fetchone()[0]==1

def test_review_and_no_payout(con):
    acknowledge_seller_rules(con,1,'2026-10-draft')
    review_seller_account(con,1,2,'approved','Weryfikacja testowa')
    status=seller_compliance_status(con,1)
    assert status['review_status']=='approved'
    assert status['can_receive_real_payouts'] is False

def test_review_requires_ack(con):
    with pytest.raises(ValueError):
        review_seller_account(con,1,2,'rejected','Brak danych')

def test_version_rejected(con):
    with pytest.raises(ValueError):
        acknowledge_seller_rules(con,1,'obsolete')

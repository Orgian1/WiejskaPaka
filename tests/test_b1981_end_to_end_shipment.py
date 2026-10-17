"""B/1981: checkout -> pickup PIN and checkout -> paid cancellation, isolated SQLite."""
import os
import tempfile
from pathlib import Path
from datetime import datetime, timedelta, timezone

os.environ['WIEJSKAPAKA_DB'] = str(Path(tempfile.mkdtemp()) / 'b1981.sqlite3')
os.environ['WP_ENABLE_TEST_PAYMENTS'] = '1'

from fastapi.testclient import TestClient
from backend.app import app, db, token_hash


def seed():
    with db() as con:
        for uid, role in [(19811, 'rolnik'), (19812, 'klient'), (19813, 'klient')]:
            con.execute('INSERT INTO users(id,email,password_hash,role) VALUES(?,?,?,?)',
                        (uid, f'b1981-{uid}@example.org', 'x', role))
            con.execute('INSERT INTO sessions(token_hash,user_id,expires_at) VALUES(?,?,?)',
                        (token_hash(f'b1981-{uid}'), uid,
                         (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()))
        for pid, price, delivery in [(19811, 1100, 200), (19812, 900, 450)]:
            con.execute('INSERT INTO products(id,farmer_id,name,price_grosze,delivery_grosze,stock) VALUES(?,?,?,?,?,?)',
                        (pid, 19811, 'Produkt', price, delivery, 10))
        con.execute('INSERT INTO pickup_points(id,farmer_id,name,city,street,opening_hours,active) VALUES(?,?,?,?,?,?,?)',
                    (19811, 19811, 'Punkt', 'Miasto', 'Ulica 1', '8-18', 1))


def headers(uid):
    return {'Authorization': f'Bearer b1981-{uid}'}


def cart(client, qty=1):
    with db() as con:
        for pid in (19811, 19812):
            con.execute('INSERT INTO saved_cart_items(buyer_id,product_id,quantity) VALUES(?,?,?)', (19812, pid, qty))


def test_complete_pickup_shipment_and_pin_privacy():
    seed()
    client = TestClient(app)
    cart(client)
    r = client.post('/cart/checkout-test', headers=headers(19812), json={'fulfillment':'odbior','pickup_point_id':19811})
    assert r.status_code == 201, r.text
    shipment = r.json()
    assert shipment['total_grosze'] == 2000
    assert shipment['delivery_grosze'] == 0
    assert len(shipment['orders']) == 2
    sid, pin = shipment['shipment_id'], shipment['shipment_pin_test_only']
    assert client.post(f'/shipments/{sid}/confirm', headers=headers(19811),
                       json={'pin':pin,'checked_goods':False}).status_code == 422
    assert client.post(f'/shipments/{sid}/confirm', headers=headers(19813),
                       json={'pin':pin,'checked_goods':True}).status_code == 403
    for order in shipment['orders']:
        assert client.post(f'/test/orders/{order["id"]}/ready', headers=headers(19811)).status_code == 200
    done = client.post(f'/shipments/{sid}/confirm', headers=headers(19811),
                       json={'pin':pin,'checked_goods':True})
    assert done.status_code == 200, done.text
    assert done.json()['confirmed_orders'] == 2
    assert client.post(f'/shipments/{sid}/confirm', headers=headers(19811),
                       json={'pin':pin,'checked_goods':True}).status_code == 409
    assert client.post(f'/shipments/{sid}/cancel-test', headers=headers(19812)).status_code == 409
    with db() as con:
        assert [r['stock'] for r in con.execute('SELECT stock FROM products WHERE id IN (19811,19812) ORDER BY id')] == [9,9]
        assert con.execute("SELECT COUNT(*) AS n FROM orders WHERE status='odebrane' AND pin_used=1").fetchone()['n'] == 2


def test_delivery_refund_restores_entire_shipment_once():
    client = TestClient(app)
    cart(client, qty=2)
    r = client.post('/cart/checkout-test', headers=headers(19812), json={
        'fulfillment':'dostawa','delivery_city':'Warszawa',
        'delivery_street':'Testowa 1','delivery_postal_code':'00-001'})
    assert r.status_code == 201, r.text
    shipment = r.json()
    assert shipment['total_grosze'] == 4450
    assert shipment['delivery_grosze'] == 450
    sid = shipment['shipment_id']
    assert client.post(f'/shipments/{sid}/cancel-paid-test', headers=headers(19813)).status_code == 404
    for order in shipment['orders']:
        payment = client.post(f'/test/payments/{order["id"]}/events', headers=headers(19812),
                              json={'event_id':f'b1981-paid-{order["id"]}', 'event_type':'payment_success_test'})
        assert payment.status_code == 200, payment.text
    cancel = client.post(f'/shipments/{sid}/cancel-paid-test', headers=headers(19812))
    assert cancel.status_code == 200, cancel.text
    assert cancel.json()['refund_grosze'] == 4450
    again = client.post(f'/shipments/{sid}/cancel-paid-test', headers=headers(19812))
    assert again.status_code == 200 and again.json()['already_processed'] is True
    assert again.json()['refund_grosze'] == 4450
    with db() as con:
        assert [r['stock'] for r in con.execute('SELECT stock FROM products WHERE id IN (19811,19812) ORDER BY id')] == [9,9]
        assert con.execute("SELECT COUNT(*) AS n FROM payment_simulation_events WHERE event_type='customer_cancel_refund_test'").fetchone()['n'] == 2


def test_unpaid_cancellation_is_atomic_and_cannot_repeat():
    client = TestClient(app)
    cart(client)
    r = client.post('/cart/checkout-test', headers=headers(19812), json={'fulfillment':'odbior','pickup_point_id':19811})
    assert r.status_code == 201, r.text
    sid = r.json()['shipment_id']
    assert client.post(f'/shipments/{sid}/cancel-test', headers=headers(19813)).status_code == 404
    first = client.post(f'/shipments/{sid}/cancel-test', headers=headers(19812))
    assert first.status_code == 200, first.text
    assert first.json()['cancelled_orders'] == 2
    assert first.json()['refund_grosze'] == 0
    assert client.post(f'/shipments/{sid}/cancel-test', headers=headers(19812)).status_code == 409
    with db() as con:
        assert [r['stock'] for r in con.execute('SELECT stock FROM products WHERE id IN (19811,19812) ORDER BY id')] == [9,9]

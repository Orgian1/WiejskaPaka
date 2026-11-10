"""Actual API/SQLite transactions: deadline, stock, whole-shipment and race cases."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from backend import app as api
from backend.inventory_reservations import HOLD_MINUTES, payment_deadline_passed
from tests.test_b10921_security_boundaries import actor


def purchase(*, cart=False):
    client = TestClient(api.app)
    farmer, _ = actor('rolnik')
    buyer, _ = actor('klient')
    products = [client.post('/products', headers=farmer, json={
        'name': 'Ziemniaki', 'price_grosze': 199, 'delivery_grosze': 500, 'stock': 10}).json()['id']
        for _ in range(2 if cart else 1)]
    body = {'fulfillment': 'dostawa', 'delivery_city': 'Opole',
            'delivery_street': 'Polna 2', 'delivery_postal_code': '45-001'}
    key = uuid4().hex
    if cart:
        for pid in products:
            assert client.put('/cart/items', headers=buyer, json={'product_id': pid, 'quantity': 2}).status_code == 200
        route = '/cart/checkout-test'
    else:
        route = '/orders'
        body.update(product_id=products[0], quantity=2)
    headers = {**buyer, 'Idempotency-Key': key}
    response = client.post(route, headers=headers, json=body)
    assert response.status_code == 201, response.text
    receipt = response.json()
    ids = [o['id'] for o in receipt['orders']] if cart else [receipt['id']]
    return client, buyer, farmer, products, ids, receipt, route, headers, body


def age(ids, *, seconds=1):
    deadline = datetime.now(timezone.utc) - timedelta(seconds=seconds)
    with api.db() as con:
        for oid in ids:
            con.execute('UPDATE inventory_reservations SET expires_at=? WHERE order_id=?',
                        (deadline.isoformat(), oid))
    return datetime.now(timezone.utc)


def state(products, ids):
    with api.db() as con:
        stocks = [con.execute('SELECT stock FROM products WHERE id=?', (p,)).fetchone()['stock'] for p in products]
        statuses = [con.execute('SELECT status FROM orders WHERE id=?', (o,)).fetchone()['status'] for o in ids]
    return stocks, statuses


def event(client, buyer, oid, kind='payment_success_test', key=None):
    return client.post(f'/test/payments/{oid}/events', headers=buyer,
                       json={'event_id': key or uuid4().hex, 'event_type': kind})


@pytest.mark.parametrize('cart', [False, True])
def test_deadline_and_exactly_once_release(cart):
    client, buyer, farmer, products, ids, receipt, route, headers, body = purchase(cart=cart)
    deadline = datetime.fromisoformat(receipt['reservation_expires_at'])
    assert timedelta(minutes=HOLD_MINUTES-1) < deadline-datetime.now(timezone.utc) <= timedelta(minutes=HOLD_MINUTES)
    api.run_reservation_expiry()
    assert state(products, ids) == ([8]*len(products), ['oczekuje_na_platnosc_testowa']*len(ids))
    now = age(ids)
    api.run_reservation_expiry(now=now)
    api.run_reservation_expiry(now=now)
    assert state(products, ids) == ([10]*len(products), ['anulowane_testowo']*len(ids))
    with api.db() as con:
        for oid in ids:
            assert con.execute("SELECT COUNT(*) AS n FROM order_events WHERE order_id=? AND event_type='reservation_expired_test'", (oid,)).fetchone()['n'] == 1
    # Same-key retry returns the original receipt/deadline; never reserves stock anew.
    assert client.post(route, headers=headers, json=body).json() == receipt
    assert state(products, ids)[0] == [10]*len(products)


@pytest.mark.parametrize('cart', [False, True])
@pytest.mark.parametrize('paid', [False, True])
def test_payment_before_deadline_protects_even_partially_paid_shipment(monkeypatch, cart, paid):
    monkeypatch.setenv('WP_ENABLE_TEST_PAYMENTS', '1')
    client, buyer, _, products, ids, *_ = purchase(cart=cart)
    if paid:
        assert event(client, buyer, ids[0]).status_code == 200
    else:
        assert event(client, buyer, ids[0], 'payment_failed_test').status_code == 200
    api.run_reservation_expiry(now=age(ids))
    assert state(products, ids)[0] == ([8] if paid else [10])*len(products)


@pytest.mark.parametrize('cart', [False, True])
def test_late_payment_cannot_claim_released_or_expired_stock(monkeypatch, cart):
    monkeypatch.setenv('WP_ENABLE_TEST_PAYMENTS', '1')
    client, buyer, _, products, ids, *_ = purchase(cart=cart)
    now = age(ids)
    for oid in ids:
        assert event(client, buyer, oid).status_code == 409
    api.run_reservation_expiry(now=now)
    for oid in ids:
        assert event(client, buyer, oid).status_code == 409
    assert state(products, ids)[0] == [10]*len(products)


def test_committed_payment_retry_after_deadline_is_readonly(monkeypatch):
    monkeypatch.setenv('WP_ENABLE_TEST_PAYMENTS', '1')
    client, buyer, _, products, ids, *_ = purchase()
    response = event(client, buyer, ids[0], key='known-success')
    assert response.status_code == 200
    age(ids)
    retry = event(client, buyer, ids[0], key='known-success')
    assert retry.status_code == 200 and retry.json() == response.json()
    assert event(client, buyer, ids[0], key='new-success').status_code == 409
    assert state(products, ids)[0] == [8]


@pytest.mark.parametrize('cart', [False, True])
def test_failed_payment_can_be_cancelled_without_refund(monkeypatch, cart):
    monkeypatch.setenv('WP_ENABLE_TEST_PAYMENTS', '1')
    client, buyer, _, products, ids, receipt, *_ = purchase(cart=cart)
    for oid in ids:
        assert event(client, buyer, oid, 'payment_failed_test').status_code == 200
    route = f'/shipments/{receipt["shipment_id"]}/cancel-test' if cart else f'/orders/{ids[0]}/cancel-test'
    response = client.post(route, headers=buyer)
    assert response.status_code == 200 and response.json()['refund_grosze'] == 0
    api.run_reservation_expiry(now=age(ids))
    assert state(products, ids)[0] == [10]*len(products)


@pytest.mark.parametrize('cart', [False, True])
def test_two_workers_and_customer_cancellation_release_only_once(cart):
    client, buyer, _, products, ids, receipt, *_ = purchase(cart=cart)
    now = age(ids)
    route = f'/shipments/{receipt["shipment_id"]}/cancel-test' if cart else f'/orders/{ids[0]}/cancel-test'
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = [pool.submit(api.run_reservation_expiry, now=now) for _ in range(2)]
        futures.append(pool.submit(client.post, route, headers=buyer))
        results = [f.result() for f in futures]
    assert results[-1].status_code in (200,409)
    assert state(products, ids) == ([10]*len(products), ['anulowane_testowo']*len(ids))


def test_failure_rolls_back_status_stock_hold_and_notifications(monkeypatch):
    _, _, _, products, ids, *_ = purchase(cart=True)
    now = age(ids)
    original = api.record_order_event
    def fail(*args):
        original(*args)
        raise RuntimeError('injected')
    monkeypatch.setattr(api, 'record_order_event', fail)
    with pytest.raises(RuntimeError):
        api.run_reservation_expiry(now=now)
    assert state(products, ids) == ([8,8], ['oczekuje_na_platnosc_testowa']*2)
    with api.db() as con:
        assert all(con.execute('SELECT released_at FROM inventory_reservations WHERE order_id=?', (oid,)).fetchone()['released_at'] is None for oid in ids)


def test_legacy_orders_are_not_retrospectively_expired():
    _, _, _, products, ids, *_ = purchase()
    age(ids)
    with api.db() as con:
        con.execute('DELETE FROM inventory_reservations WHERE order_id=?', (ids[0],))
        assert not payment_deadline_passed(con, ids[0], now=datetime.now(timezone.utc))
    api.run_reservation_expiry()
    assert state(products, ids)[0] == [8]


def test_lifespan_actually_runs_background_expiration():
    _, _, _, products, ids, *_ = purchase()
    age(ids)
    import time
    with TestClient(api.app):
        until = time.monotonic()+5
        while state(products, ids)[0] != [10] and time.monotonic()<until:
            time.sleep(0.01)
        assert state(products, ids)[0] == [10]


def test_capacity_limit_cannot_be_bypassed_by_same_buyer(monkeypatch):
    from backend.inventory_reservations import MAX_UNPAID_PURCHASES
    client, buyer, _, products, ids, receipt, route, headers, body = purchase()
    # Increase stock for ten independent holds on the same test product.
    with api.db() as con:
        con.execute('UPDATE products SET stock=100 WHERE id=?', (products[0],))
    for _ in range(MAX_UNPAID_PURCHASES-1):
        assert client.post(route, headers=buyer, json=body).status_code == 201
    blocked = client.post(route, headers=buyer, json=body)
    assert blocked.status_code == 409 and 'Limit 10' in blocked.text
    assert client.post(route, headers=headers, json=body).json() == receipt
    assert client.post(f'/orders/{ids[0]}/cancel-test', headers=buyer).status_code == 200
    assert client.post(route, headers=buyer, json=body).status_code == 201


def test_paid_and_failed_lines_can_be_refunded_as_a_whole(monkeypatch):
    monkeypatch.setenv('WP_ENABLE_TEST_PAYMENTS', '1')
    client, buyer, _, products, ids, receipt, *_ = purchase(cart=True)
    assert event(client, buyer, ids[0]).status_code == 200
    assert event(client, buyer, ids[1], 'payment_failed_test').status_code == 200
    response = client.post(f'/shipments/{receipt["shipment_id"]}/cancel-paid-test', headers=buyer)
    assert response.status_code == 200, response.text
    assert response.json()['refund_grosze'] == 898
    assert state(products, ids)[0] == [10,10]


def test_concurrent_payment_and_expiration_cannot_sell_released_stock(monkeypatch):
    monkeypatch.setenv('WP_ENABLE_TEST_PAYMENTS', '1')
    client, buyer, _, products, ids, receipt, *_ = purchase()
    # A sweep just after deadline races with a current payment. Either the
    # already committed payment protects stock, or closure rejects payment.
    future = datetime.fromisoformat(receipt['reservation_expires_at'])+timedelta(seconds=1)
    with ThreadPoolExecutor(max_workers=2) as pool:
        expiry = pool.submit(api.run_reservation_expiry, now=future)
        payment = pool.submit(event, client, buyer, ids[0])
        expiry.result()
        result = payment.result()
    assert result.status_code in (200,409)
    with api.db() as con:
        p = api.get_payment(con, ids[0])
    if result.status_code == 200:
        assert p.state == 'paid_test'
        assert state(products, ids) == ([8], ['oczekuje_na_platnosc_testowa'])
    else:
        assert p is None
        assert state(products, ids) == ([10], ['anulowane_testowo'])


@pytest.mark.parametrize('paid', [False, True])
def test_expired_unpaid_direct_delivery_cannot_escape_expiration_by_dispatch(monkeypatch, paid):
    monkeypatch.setenv('WP_ENABLE_TEST_PAYMENTS', '1')
    client, buyer, farmer, products, ids, *_ = purchase()
    courier, cid = actor('dostawca')
    assert client.post(f'/orders/{ids[0]}/assign-courier-test', headers=farmer, json={'courier_id':cid}).status_code == 200
    if paid:
        assert event(client,buyer,ids[0]).status_code == 200
    age(ids)
    response = client.post(f'/orders/{ids[0]}/dispatch-test', headers=farmer)
    assert response.status_code == (200 if paid else 409)
    api.run_reservation_expiry()
    assert state(products, ids)[0] == ([8] if paid else [10])


@pytest.mark.parametrize('paid_count', [0,1,2])
def test_shipment_dispatch_deadline_is_atomic(monkeypatch, paid_count):
    monkeypatch.setenv('WP_ENABLE_TEST_PAYMENTS', '1')
    client,buyer,farmer,products,ids,receipt,*_ = purchase(cart=True)
    _, cid = actor('dostawca')
    assert client.post(f'/shipments/{receipt["shipment_id"]}/assign-courier-test', headers=farmer, json={'courier_id':cid}).status_code == 200
    for oid in ids[:paid_count]:
        assert event(client,buyer,oid).status_code == 200
    age(ids)
    response = client.post(f'/shipments/{receipt["shipment_id"]}/dispatch-test', headers=farmer)
    assert response.status_code == (200 if paid_count == 2 else 409)
    assert state(products,ids)[1] == (['w_drodze_testowo']*2 if paid_count == 2 else ['oczekuje_na_platnosc_testowa']*2)


@pytest.mark.parametrize('paid', [False,True])
def test_pickup_ready_respects_unpaid_deadline(monkeypatch, paid):
    monkeypatch.setenv('WP_ENABLE_TEST_PAYMENTS', '1')
    client,buyer,farmer,products,*_ = purchase()
    point = client.post('/pickup-points', headers=farmer, json={'name':'Punkt','city':'Opole','street':'Polna 2','opening_hours':'9-17'}).json()['id']
    receipt = client.post('/orders', headers=buyer, json={'product_id':products[0],'quantity':1,'fulfillment':'odbior','pickup_point_id':point}).json()
    oid = receipt['id']
    if paid:
        assert event(client,buyer,oid).status_code == 200
    age([oid])
    assert client.post(f'/test/orders/{oid}/ready', headers=farmer).status_code == (200 if paid else 409)


def test_protected_shipments_cannot_starve_next_expiry_batch(monkeypatch):
    from backend.inventory_reservations import expire_due
    monkeypatch.setenv('WP_ENABLE_TEST_PAYMENTS', '1')
    client,buyer,_,products,ids,*_ = purchase(cart=True)
    assert event(client,buyer,ids[0]).status_code == 200
    age(ids,seconds=1_000_000)
    _,_,_,other_products,other_ids,*_ = purchase()
    now = age(other_ids,seconds=999_999)
    with api.db() as con:
        con.execute('BEGIN IMMEDIATE')
        report = expire_due(con, now=now, record_event=api.record_order_event, limit=1)
    assert report['expired_orders'] == 1
    assert state(other_products,other_ids)[0] == [10]
    assert state(products,ids)[0] == [8,8]

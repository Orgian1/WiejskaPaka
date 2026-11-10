"""Refund invariants beyond status-only and source-text checks."""
from dataclasses import replace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from backend import app as api
from backend.payment_integrity import audit_payment_integrity
from backend.payment_simulator import new_payment, apply_event
from tests.test_b10921_security_boundaries import actor


def purchase(client, *, cart=False, event_id=None):
    farmer, fid = actor('rolnik')
    buyer, bid = actor('klient')
    courier, cid = actor('dostawca')
    products = [client.post('/products', headers=farmer, json={
        'name': 'Jabłka', 'price_grosze': price, 'delivery_grosze': fee, 'stock': 10}).json()['id']
        for price, fee in [(199, 501), (301, 399)]]
    body = {'fulfillment': 'dostawa', 'delivery_city': 'Legnica',
            'delivery_street': 'Polna 1', 'delivery_postal_code': '59-220'}
    if cart:
        for pid in products:
            assert client.put('/cart/items', headers=buyer, json={'product_id': pid, 'quantity': 2}).status_code == 200
        result = client.post('/cart/checkout-test', headers=buyer, json=body).json()
        ids = [o['id'] for o in result['orders']]
    else:
        result = client.post('/orders', headers=buyer, json={**body, 'product_id': products[0], 'quantity': 2}).json()
        ids = [result['id']]
    for oid in ids:
        response = client.post(f'/test/payments/{oid}/events', headers=buyer,
                              json={'event_id': event_id or uuid4().hex, 'event_type': 'payment_success_test'})
        assert response.status_code == 200, response.text
    return farmer, buyer, courier, cid, result, ids


@pytest.mark.parametrize('cart', [False, True])
def test_customer_refund_is_valid_for_financial_audit(monkeypatch, cart):
    monkeypatch.setenv('WP_ENABLE_TEST_PAYMENTS', '1')
    client = TestClient(api.app)
    farmer, buyer, courier, cid, result, ids = purchase(client, cart=cart)
    url = f'/shipments/{result["shipment_id"]}/cancel-paid-test' if cart else f'/orders/{ids[0]}/cancel-paid-test'
    response = client.post(url, headers=buyer)
    assert response.status_code == 200, response.text
    with api.db() as con:
        report = audit_payment_integrity(con)
        assert report['ok'], report
        for oid in ids:
            payment = api.get_payment(con, oid)
            assert payment.refund_grosze == payment.total_grosze
            assert payment.payout_grosze == 0


def test_one_line_refund_cannot_break_a_paid_shipment(monkeypatch):
    monkeypatch.setenv('WP_ENABLE_TEST_PAYMENTS', '1')
    client = TestClient(api.app)
    farmer, buyer, courier, cid, result, ids = purchase(client, cart=True)
    shipment = result['shipment_id']
    assert client.post(f'/shipments/{shipment}/assign-courier-test', headers=farmer, json={'courier_id': cid}).status_code == 200
    assert client.post(f'/shipments/{shipment}/dispatch-test', headers=farmer).status_code == 200
    partial = client.post(f'/test/payments/{ids[0]}/events', headers=farmer,
                          json={'event_id': uuid4().hex, 'event_type': 'delivery_failed_by_courier_test'})
    assert partial.status_code == 409
    response = client.post(f'/shipments/{shipment}/courier-failure-test', headers=farmer,
                           json={'reason': 'dostawca_nie_przyjechal'})
    assert response.status_code == 200, response.text
    assert response.json()['refund_grosze'] == result['total_grosze'] == 1501
    assert client.get('/couriers/me/active-addresses', headers=courier).json() == []
    with api.db() as con:
        assert audit_payment_integrity(con)['ok']


@pytest.mark.parametrize('state,refund,payout', [
    ('paid_test', 1, 0), ('completed_test', 0, 1),
    ('refunded_test', 0, 0), ('paid_out_test', 0, 0), ('unknown', 0, 0),
])
def test_payment_transition_rejects_inconsistent_persisted_state(state, refund, payout):
    payment = replace(new_payment(1, 100, 10), state=state, refund_grosze=refund, payout_grosze=payout)
    with pytest.raises(ValueError):
        # Replaying a known ID must still validate persisted financial state.
        apply_event(replace(payment, processed_event_ids=frozenset({'known'})), 'known', 'order_completed_test')


def test_other_customer_cannot_reserve_internal_refund_identifier(monkeypatch):
    monkeypatch.setenv('WP_ENABLE_TEST_PAYMENTS', '1')
    client = TestClient(api.app)
    farmer, buyer, _, _, _, ids = purchase(client)
    purchase(client, event_id=f'cancel-paid-order:{ids[0]}')
    response = client.post(f'/orders/{ids[0]}/cancel-paid-test', headers=buyer)
    assert response.status_code == 200, response.text
    assert response.json()['refund_grosze'] == 899


def test_same_external_key_on_other_orders_is_independent(monkeypatch):
    monkeypatch.setenv('WP_ENABLE_TEST_PAYMENTS', '1')
    client = TestClient(api.app)
    purchase(client, cart=True, event_id='payment-attempt-1')
    purchase(client, event_id='payment-attempt-1')


def test_concurrent_direct_cancellation_restores_inventory_only_once(monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    monkeypatch.setenv('WP_ENABLE_TEST_PAYMENTS', '1')
    client = TestClient(api.app)
    farmer, buyer, _, _, _, ids = purchase(client)
    oid = ids[0]
    url = f'/orders/{oid}/cancel-paid-test'
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(lambda _: TestClient(api.app).post(url, headers=buyer), range(2)))
    assert [r.status_code for r in responses] == [200, 200]
    assert sorted(r.json()['already_processed'] for r in responses) == [False, True]
    with api.db() as con:
        assert con.execute('SELECT stock FROM products WHERE id=(SELECT product_id FROM orders WHERE id=?)',
                           (oid,)).fetchone()['stock'] == 10
        assert con.execute("SELECT COUNT(*) AS n FROM payment_simulation_events WHERE order_id=? AND event_type='customer_cancel_refund_test'",
                           (oid,)).fetchone()['n'] == 1
        assert audit_payment_integrity(con)['ok']


def test_direct_cancellation_authorization_and_disabled_flag(monkeypatch):
    monkeypatch.setenv('WP_ENABLE_TEST_PAYMENTS', '1')
    client = TestClient(api.app)
    farmer, buyer, courier, _, _, ids = purchase(client)
    stranger, _ = actor('klient')
    url = f'/orders/{ids[0]}/cancel-paid-test'
    assert client.post(url).status_code == 401
    assert client.post(url, headers=farmer).status_code == 403
    assert client.post(url, headers=courier).status_code == 403
    assert client.post(url, headers=stranger).status_code == 404
    monkeypatch.delenv('WP_ENABLE_TEST_PAYMENTS')
    assert client.post(url, headers=buyer).status_code == 404
    with api.db() as con:
        assert api.get_payment(con, ids[0]).state == 'paid_test'


def test_failed_refund_transaction_does_not_restore_stock(monkeypatch):
    monkeypatch.setenv('WP_ENABLE_TEST_PAYMENTS', '1')
    client = TestClient(api.app)
    _, buyer, _, _, _, ids = purchase(client)
    original = api.persist_event

    def fail_after_event(*args, **kwargs):
        original(*args, **kwargs)
        raise RuntimeError('injected failure after recording refund')

    monkeypatch.setattr(api, 'persist_event', fail_after_event)
    response = TestClient(api.app, raise_server_exceptions=False).post(
        f'/orders/{ids[0]}/cancel-paid-test', headers=buyer)
    assert response.status_code == 500
    assert response.headers['cache-control'] == 'no-store'
    assert response.headers['x-content-type-options'] == 'nosniff'
    assert 'injected failure' not in response.text
    with api.db() as con:
        assert api.get_payment(con, ids[0]).state == 'paid_test'
        assert con.execute('SELECT stock FROM products WHERE id=(SELECT product_id FROM orders WHERE id=?)',
                           (ids[0],)).fetchone()['stock'] == 8
        assert con.execute("SELECT COUNT(*) AS n FROM payment_simulation_events WHERE order_id=? AND event_type='customer_cancel_refund_test'",
                           (ids[0],)).fetchone()['n'] == 0

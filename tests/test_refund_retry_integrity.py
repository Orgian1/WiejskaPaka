"""A retry must revalidate persisted money, not merely the terminal order status."""
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from backend import app as api
from tests.test_purchase_records import purchase
from tests.test_transaction_session_boundaries import database_digest


def pay(client, buyer, oid):
    response = client.post(f'/test/payments/{oid}/events', headers=buyer,
                          json={'event_id': uuid4().hex, 'event_type': 'payment_success_test'})
    assert response.status_code == 200, response.text


@pytest.mark.parametrize('cart', [False, True])
@pytest.mark.parametrize('corruption', ['paid-state', 'partial-refund', 'payout', 'different-total'])
def test_refund_retry_rejects_corrupted_payment_without_writes(monkeypatch, cart, corruption):
    monkeypatch.setenv('WP_ENABLE_TEST_PAYMENTS', '1')
    client, farmer, buyer, products, point, point_body, receipt, ids, *_ = purchase(cart=cart)
    for oid in ids:
        pay(client, buyer, oid)
    url = f'/shipments/{receipt["shipment_id"]}/cancel-paid-test' if cart else f'/orders/{ids[0]}/cancel-paid-test'
    first = client.post(url, headers=buyer)
    assert first.status_code == 200 and not first.json()['already_processed']
    changes = {
        'paid-state': "state='paid_test',refund_grosze=0",
        'partial-refund': 'refund_grosze=refund_grosze-1',
        'payout': 'payout_grosze=1',
        'different-total': 'total_grosze=total_grosze+1,products_grosze=products_grosze+1,seller_grosze=seller_grosze+1,refund_grosze=refund_grosze+1',
    }
    with api.db() as con:
        con.execute('UPDATE payment_simulations SET '+changes[corruption]+' WHERE order_id=?', (ids[-1],))
    before = database_digest()
    response = client.post(url, headers=buyer)
    assert response.status_code == 409, response.text
    assert database_digest() == before


@pytest.mark.parametrize('retry', [False, True])
@pytest.mark.parametrize('corruption', ['different-total', 'payout'])
def test_courier_failure_validates_money_before_first_refund_and_retry(monkeypatch, retry, corruption):
    from tests.test_b10921_security_boundaries import actor
    monkeypatch.setenv('WP_ENABLE_TEST_PAYMENTS', '1')
    client, farmer, buyer, products, point, point_body, receipt, ids, *_ = purchase(cart=True, fulfillment='dostawa')
    courier, cid = actor('dostawca')
    for oid in ids:
        pay(client, buyer, oid)
    shipment = receipt['shipment_id']
    assert client.post(f'/shipments/{shipment}/assign-courier-test', headers=farmer, json={'courier_id': cid}).status_code == 200
    assert client.post(f'/shipments/{shipment}/dispatch-test', headers=farmer).status_code == 200
    url = f'/shipments/{shipment}/courier-failure-test'
    body = {'reason': 'dostawca_nie_przyjechal'}
    if retry:
        assert client.post(url, headers=farmer, json=body).status_code == 200
    with api.db() as con:
        if corruption == 'payout':
            con.execute('UPDATE payment_simulations SET payout_grosze=1 WHERE order_id=?', (ids[-1],))
        else:
            con.execute('UPDATE payment_simulations SET total_grosze=total_grosze+1,products_grosze=products_grosze+1,seller_grosze=seller_grosze+1,refund_grosze=refund_grosze+? WHERE order_id=?', (int(retry), ids[-1]))
    before = database_digest()
    response = TestClient(api.app, raise_server_exceptions=False).post(url, headers=farmer, json=body)
    assert response.status_code == 409, response.text
    assert database_digest() == before


def test_existing_payment_must_match_order_before_simulated_payment_event(monkeypatch):
    monkeypatch.setenv('WP_ENABLE_TEST_PAYMENTS', '1')
    client, farmer, buyer, products, point, point_body, receipt, ids, *_ = purchase()
    with api.db() as con:
        order = con.execute('SELECT * FROM orders WHERE id=?', (ids[0],)).fetchone()
        api.create_payment(con, order)
        con.execute('UPDATE payment_simulations SET total_grosze=total_grosze+1,products_grosze=products_grosze+1,seller_grosze=seller_grosze+1 WHERE order_id=?', (ids[0],))
    before = database_digest()
    response = client.post(f'/test/payments/{ids[0]}/events', headers=buyer,
                           json={'event_id': uuid4().hex, 'event_type': 'payment_success_test'})
    assert response.status_code == 409, response.text
    assert database_digest() == before


@pytest.mark.parametrize('cart', [False, True])
def test_first_refund_rejects_internally_valid_payment_for_different_amount(monkeypatch, cart):
    monkeypatch.setenv('WP_ENABLE_TEST_PAYMENTS', '1')
    client, farmer, buyer, products, point, point_body, receipt, ids, *_ = purchase(cart=cart)
    for oid in ids:
        pay(client, buyer, oid)
    with api.db() as con:
        con.execute('UPDATE payment_simulations SET total_grosze=total_grosze+1,products_grosze=products_grosze+1,seller_grosze=seller_grosze+1 WHERE order_id=?', (ids[-1],))
    before = database_digest()
    url = f'/shipments/{receipt["shipment_id"]}/cancel-paid-test' if cart else f'/orders/{ids[0]}/cancel-paid-test'
    response = client.post(url, headers=buyer)
    assert response.status_code == 409, response.text
    assert database_digest() == before


def test_unpaid_cancellation_cannot_be_reported_as_successful_paid_refund(monkeypatch):
    monkeypatch.setenv('WP_ENABLE_TEST_PAYMENTS', '1')
    client, farmer, buyer, products, point, point_body, receipt, ids, *_ = purchase(cart=True)
    assert client.post(f'/shipments/{receipt["shipment_id"]}/cancel-test', headers=buyer).status_code == 200
    before = database_digest()
    assert client.post(f'/shipments/{receipt["shipment_id"]}/cancel-paid-test', headers=buyer).status_code == 409
    assert database_digest() == before


@pytest.mark.parametrize('unpaid_state', ['absent', 'awaiting_payment', 'failed_test'])
def test_mixed_shipment_retry_refunds_only_paid_items_once(monkeypatch, unpaid_state):
    monkeypatch.setenv('WP_ENABLE_TEST_PAYMENTS', '1')
    client, farmer, buyer, products, point, point_body, receipt, ids, *_ = purchase(cart=True)
    pay(client, buyer, ids[0])
    if unpaid_state != 'absent':
        with api.db() as con:
            order = con.execute('SELECT * FROM orders WHERE id=?', (ids[1],)).fetchone()
            payment = api.create_payment(con, order)
            if unpaid_state == 'failed_test':
                api.persist_event(con, payment, uuid4().hex, 'payment_failed_test', '2026-10-17T12:00:00+00:00')
    url = f'/shipments/{receipt["shipment_id"]}/cancel-paid-test'
    first = client.post(url, headers=buyer)
    assert first.status_code == 200
    with api.db() as con:
        expected = con.execute('SELECT total_grosze FROM orders WHERE id=?', (ids[0],)).fetchone()[0]
    assert first.json()['refund_grosze'] == expected
    before = database_digest()
    second = client.post(url, headers=buyer)
    assert second.status_code == 200 and second.json()['already_processed']
    assert second.json()['refund_grosze'] == expected
    assert database_digest() == before

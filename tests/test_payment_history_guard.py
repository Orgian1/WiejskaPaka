"""Persisted event evidence must explain the payment snapshot before writes/retries."""
from uuid import uuid4

import pytest

from backend import app as api
from tests.test_purchase_records import purchase
from tests.test_refund_retry_integrity import pay
from tests.test_transaction_session_boundaries import database_digest


@pytest.mark.parametrize('cart', [False, True])
@pytest.mark.parametrize('corruption', ['missing-paid', 'missing-refund', 'wrong-state', 'unknown-event', 'duplicate-paid'])
def test_refund_retry_rejects_history_that_does_not_explain_snapshot(monkeypatch, cart, corruption):
    monkeypatch.setenv('WP_ENABLE_TEST_PAYMENTS', '1')
    client, farmer, buyer, products, point, point_body, receipt, ids, *_ = purchase(cart=cart)
    for oid in ids:
        pay(client, buyer, oid)
    url = f'/shipments/{receipt["shipment_id"]}/cancel-paid-test' if cart else f'/orders/{ids[0]}/cancel-paid-test'
    assert client.post(url, headers=buyer).status_code == 200
    oid = ids[-1]
    with api.db() as con:
        if corruption == 'missing-paid':
            con.execute("DELETE FROM payment_simulation_events WHERE order_id=? AND event_type='payment_success_test'", (oid,))
        elif corruption == 'missing-refund':
            con.execute("DELETE FROM payment_simulation_events WHERE order_id=? AND event_type='customer_cancel_refund_test'", (oid,))
        elif corruption == 'wrong-state':
            con.execute("UPDATE payment_simulation_events SET state_after='paid_test' WHERE order_id=? AND event_type='customer_cancel_refund_test'", (oid,))
        elif corruption == 'unknown-event':
            con.execute("UPDATE payment_simulation_events SET event_type='unknown' WHERE order_id=? AND event_type='customer_cancel_refund_test'", (oid,))
        else:
            con.execute('INSERT INTO payment_simulation_events VALUES(?,?,?,?,?)',
                        (uuid4().hex, oid, 'payment_success_test', 'paid_test', 'same-time'))
    before = database_digest()
    response = client.post(url, headers=buyer)
    assert response.status_code == 409, response.text
    assert database_digest() == before


@pytest.mark.parametrize('cart', [False, True])
def test_first_refund_requires_history_of_payment(monkeypatch, cart):
    monkeypatch.setenv('WP_ENABLE_TEST_PAYMENTS', '1')
    client, farmer, buyer, products, point, point_body, receipt, ids, *_ = purchase(cart=cart)
    for oid in ids:
        pay(client, buyer, oid)
    with api.db() as con:
        con.execute('DELETE FROM payment_simulation_events WHERE order_id=?', (ids[-1],))
    before = database_digest()
    url = f'/shipments/{receipt["shipment_id"]}/cancel-paid-test' if cart else f'/orders/{ids[0]}/cancel-paid-test'
    assert client.post(url, headers=buyer).status_code == 409
    assert database_digest() == before


def test_payment_event_retry_requires_consistent_saved_history(monkeypatch):
    monkeypatch.setenv('WP_ENABLE_TEST_PAYMENTS', '1')
    client, farmer, buyer, products, point, point_body, receipt, ids, *_ = purchase()
    body = {'event_id': uuid4().hex, 'event_type': 'payment_success_test'}
    url = f'/test/payments/{ids[0]}/events'
    assert client.post(url, headers=buyer, json=body).status_code == 200
    with api.db() as con:
        con.execute("UPDATE payment_simulation_events SET state_after='refunded_test' WHERE order_id=?", (ids[0],))
    before = database_digest()
    assert client.post(url, headers=buyer, json=body).status_code == 409
    assert database_digest() == before


@pytest.mark.parametrize('timestamps', ['same', 'reversed'])
def test_valid_history_does_not_depend_on_timestamp_order(monkeypatch, timestamps):
    monkeypatch.setenv('WP_ENABLE_TEST_PAYMENTS', '1')
    client, farmer, buyer, products, point, point_body, receipt, ids, *_ = purchase(cart=True)
    for oid in ids:
        pay(client, buyer, oid)
    url = f'/shipments/{receipt["shipment_id"]}/cancel-paid-test'
    first = client.post(url, headers=buyer)
    assert first.status_code == 200
    with api.db() as con:
        con.execute('UPDATE payment_simulation_events SET created_at=? WHERE order_id IN (?,?)', ('2026-10-17T12:00:00Z', *ids))
        if timestamps == 'reversed':
            con.execute("UPDATE payment_simulation_events SET created_at='2026-10-16T12:00:00Z' WHERE order_id IN (?,?) AND event_type='customer_cancel_refund_test'", ids)
    before = database_digest()
    second = client.post(url, headers=buyer)
    assert second.status_code == 200 and second.json()['already_processed']
    assert second.json()['refund_grosze'] == first.json()['refund_grosze']
    assert database_digest() == before

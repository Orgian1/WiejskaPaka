"""B/51-55: integration regressions for test-only courier failure and privacy."""
import uuid
import pytest
from tests.test_api import c, reg
from tests.test_stabilization_02 import _new_delivery


def setup_delivery(label):
    farmer, buyer, courier, other, order = _new_delivery(f'b55-{label}-{uuid.uuid4().hex[:8]}')
    oid = order['id']
    courier_id = c.get('/auth/me', headers=courier).json()['id']
    assert c.post(f'/orders/{oid}/assign-courier-test', headers=farmer,
                  json={'courier_id': courier_id}).status_code == 200
    return farmer, buyer, courier, other, order


def event(oid, headers, kind, key):
    return c.post(f'/test/payments/{oid}/events', headers=headers,
                  json={'event_type': kind, 'event_id': key})


def test_b51_cannot_refund_before_dispatch(monkeypatch):
    monkeypatch.setenv('WP_ENABLE_TEST_PAYMENTS', '1')
    farmer, buyer, courier, other, order = setup_delivery('pre')
    oid = order['id']
    assert event(oid, buyer, 'payment_success_test', f'pay-{oid}').status_code == 200
    result = event(oid, farmer, 'delivery_failed_by_courier_test', f'refund-{oid}')
    assert result.status_code == 409
    assert c.get(f'/orders/{oid}/location', headers=courier).status_code == 403


def test_b52_refund_revokes_address_and_preserves_total(monkeypatch):
    monkeypatch.setenv('WP_ENABLE_TEST_PAYMENTS', '1')
    farmer, buyer, courier, other, order = setup_delivery('refund')
    oid = order['id']
    assert event(oid, buyer, 'payment_success_test', f'pay-{oid}').status_code == 200
    assert c.post(f'/orders/{oid}/dispatch-test', headers=farmer).status_code == 200
    assert c.get(f'/orders/{oid}/location', headers=courier).status_code == 200
    result = event(oid, farmer, 'delivery_failed_by_courier_test', f'refund-{oid}')
    assert result.status_code == 200, result.text
    assert result.json()['refund_grosze'] == order['total_grosze']
    assert result.json()['state'] == 'refunded_test'
    assert c.get(f'/orders/{oid}/location', headers=courier).status_code == 403
    assert all(row['order_id'] != oid for row in c.get('/couriers/me/active-addresses', headers=courier).json())
    assert any(row['id'] == oid and row['status'] == 'nieudana_dostawa_testowo'
               for row in c.get('/orders/me', headers=buyer).json())


def test_b53_refund_same_event_id_is_idempotent(monkeypatch):
    monkeypatch.setenv('WP_ENABLE_TEST_PAYMENTS', '1')
    farmer, buyer, courier, other, order = setup_delivery('retry')
    oid = order['id']
    assert event(oid, buyer, 'payment_success_test', f'pay-{oid}').status_code == 200
    assert c.post(f'/orders/{oid}/dispatch-test', headers=farmer).status_code == 200
    first = event(oid, farmer, 'delivery_failed_by_courier_test', f'refund-{oid}')
    second = event(oid, farmer, 'delivery_failed_by_courier_test', f'refund-{oid}')
    assert first.status_code == second.status_code == 200
    assert first.json() == second.json()
    assert event(oid, farmer, 'delivery_failed_by_courier_test', f'refund-new-{oid}').status_code == 409


def test_b54_refund_permissions_and_no_premature_disclosure(monkeypatch):
    monkeypatch.setenv('WP_ENABLE_TEST_PAYMENTS', '1')
    farmer, buyer, courier, other, order = setup_delivery('permissions')
    oid = order['id']
    assert event(oid, buyer, 'payment_success_test', f'pay-{oid}').status_code == 200
    assert c.post(f'/orders/{oid}/dispatch-test', headers=farmer).status_code == 200
    for role in (buyer, courier, other):
        assert event(oid, role, 'delivery_failed_by_courier_test', f'bad-{uuid.uuid4().hex}').status_code == 403
    assert c.get(f'/orders/{oid}/location', headers=other).status_code == 403
    assert c.get(f'/orders/{oid}/location', headers=courier).status_code == 200


def test_b55_cannot_refund_delivered_order(monkeypatch):
    monkeypatch.setenv('WP_ENABLE_TEST_PAYMENTS', '1')
    farmer, buyer, courier, other, order = setup_delivery('delivered')
    oid = order['id']
    assert event(oid, buyer, 'payment_success_test', f'pay-{oid}').status_code == 200
    assert c.post(f'/orders/{oid}/dispatch-test', headers=farmer).status_code == 200
    confirmed = c.post(f'/orders/{oid}/confirm', headers=courier,
                       json={'pin': order['pin_test_only'], 'checked_goods': True})
    assert confirmed.status_code == 200
    assert event(oid, farmer, 'delivery_failed_by_courier_test', f'refund-{oid}').status_code == 409
    assert c.get(f'/orders/{oid}/location', headers=courier).status_code == 403

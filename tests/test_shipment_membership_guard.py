"""Corrupt links must never grant authority over another buyer's/seller's order."""
from uuid import uuid4

import pytest

from backend import app as api
from tests.test_b10921_security_boundaries import actor
from tests.test_purchase_records import purchase
from tests.test_transaction_session_boundaries import database_digest


@pytest.mark.parametrize('operation', ['confirm', 'cancel', 'cancel-paid', 'assign-courier', 'dispatch', 'courier-failure'])
@pytest.mark.parametrize('field', ['buyer_id', 'farmer_id', 'fulfillment'])
def test_inconsistent_shipment_rejected_before_any_write(monkeypatch, operation, field):
    monkeypatch.setenv('WP_ENABLE_TEST_PAYMENTS', '1')
    fulfillment = 'odbior' if operation == 'confirm' else 'dostawa'
    client, farmer, buyer, products, point, point_body, receipt, ids, *_ = purchase(cart=True, fulfillment=fulfillment)
    shipment = receipt['shipment_id']
    courier, cid = actor('dostawca')
    if operation in ('cancel-paid', 'courier-failure'):
        for oid in ids:
            response = client.post(f'/test/payments/{oid}/events', headers=buyer,
                                  json={'event_id': uuid4().hex, 'event_type': 'payment_success_test'})
            assert response.status_code == 200, response.text
    if operation in ('dispatch', 'courier-failure'):
        assert client.post(f'/shipments/{shipment}/assign-courier-test', headers=farmer,
                           json={'courier_id': cid}).status_code == 200
    if operation == 'courier-failure':
        assert client.post(f'/shipments/{shipment}/dispatch-test', headers=farmer).status_code == 200
    if field == 'fulfillment':
        value = 'dostawa' if fulfillment == 'odbior' else 'odbior'
    else:
        _, value = actor('klient' if field == 'buyer_id' else 'rolnik')
    with api.db() as con:
        if operation == 'confirm':
            for oid in ids:
                con.execute("UPDATE orders SET status='gotowe_do_odbioru_testowo' WHERE id=?", (oid,))
        # Fixed parameterized field names above; no external SQL identifiers.
        con.execute(f'UPDATE orders SET {field}=? WHERE id=?', (value, ids[-1]))
    before = database_digest()
    suffix = operation if operation == 'confirm' else operation + '-test'
    payload = {'confirm': {'pin': receipt['shipment_pin_test_only'], 'checked_goods': True},
               'assign-courier': {'courier_id': cid},
               'courier-failure': {'reason': 'dostawca_nie_przyjechal'}}.get(operation)
    response = client.post(f'/shipments/{shipment}/{suffix}',
                           headers=buyer if operation in ('cancel', 'cancel-paid') else farmer,
                           json=payload)
    assert response.status_code == 409, response.text
    assert database_digest() == before

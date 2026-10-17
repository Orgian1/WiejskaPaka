"""A valid payment graph must also agree with the order's closure and actor."""
from uuid import uuid4

import pytest

from backend import app as api
from tests.test_b10921_security_boundaries import actor
from tests.test_purchase_records import purchase
from tests.test_refund_retry_integrity import pay
from tests.test_transaction_session_boundaries import database_digest


@pytest.mark.parametrize('route', ['cancel-order', 'cancel-shipment', 'failure-order', 'failure-shipment'])
@pytest.mark.parametrize('corruption', [None, 'reason', 'missing-closure', 'previous-status', 'actor', 'duplicate-closure'])
def test_retry_requires_matching_order_closure(monkeypatch, route, corruption):
    monkeypatch.setenv('WP_ENABLE_TEST_PAYMENTS', '1')
    cart = route.endswith('shipment')
    failure = route.startswith('failure')
    client, farmer, buyer, products, point, point_body, receipt, ids, *_ = purchase(
        cart=cart, fulfillment='dostawa' if failure else 'odbior')
    for oid in ids:
        pay(client, buyer, oid)
    root = f'/shipments/{receipt["shipment_id"]}' if cart else f'/orders/{ids[0]}'
    body = None
    headers = buyer
    if failure:
        courier, cid = actor('dostawca')
        assert client.post(root+'/assign-courier-test', headers=farmer, json={'courier_id': cid}).status_code == 200
        assert client.post(root+'/dispatch-test', headers=farmer).status_code == 200
        headers = farmer
        if cart:
            url = root+'/courier-failure-test'
            body = {'reason': 'dostawca_nie_przyjechal'}
        else:
            url = f'/test/payments/{ids[0]}/events'
            body = {'event_id': uuid4().hex, 'event_type': 'delivery_failed_by_courier_test'}
    else:
        url = root+'/cancel-paid-test'
    first = client.post(url, headers=headers, json=body)
    assert first.status_code == 200, first.text
    oid = ids[-1]
    terminal = 'nieudana_dostawa_testowo' if failure else 'anulowane_testowo'
    with api.db() as con:
        if corruption == 'reason':
            other = 'customer_cancel_refund_test' if failure else 'delivery_failed_by_courier_test'
            con.execute("UPDATE payment_simulation_events SET event_type=? WHERE order_id=? AND state_after='refunded_test'", (other, oid))
        elif corruption == 'missing-closure':
            con.execute('DELETE FROM order_events WHERE order_id=? AND new_status=?', (oid, terminal))
        elif corruption == 'previous-status':
            con.execute("UPDATE order_events SET previous_status='odebrane' WHERE order_id=? AND new_status=?", (oid, terminal))
        elif corruption == 'actor':
            # A valid existing account, but not the actor authorized for this closure.
            other_id = con.execute('SELECT buyer_id,farmer_id FROM orders WHERE id=?', (oid,)).fetchone()
            con.execute('UPDATE order_events SET actor_id=? WHERE order_id=? AND new_status=?',
                        (other_id['buyer_id'] if failure else other_id['farmer_id'], oid, terminal))
        elif corruption == 'duplicate-closure':
            con.execute('''INSERT INTO order_events(order_id,actor_id,event_type,previous_status,new_status,created_at)
                SELECT order_id,actor_id,event_type,previous_status,new_status,created_at
                FROM order_events WHERE order_id=? AND new_status=?''', (oid, terminal))
    before = database_digest()
    second = client.post(url, headers=headers, json=body)
    assert second.status_code == (200 if corruption is None else 409), second.text
    if corruption is None:
        assert second.json()['refund_grosze'] == first.json()['refund_grosze']
    assert database_digest() == before

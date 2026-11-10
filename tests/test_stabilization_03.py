"""Privacy regression: courier address access expires on delivery completion."""
from tests.test_stabilization_02 import _new_delivery
from tests.test_api import c

def test_courier_loses_address_after_successful_delivery():
    farmer, buyer, courier, other, order = _new_delivery('expire-03')
    oid = order['id']
    courier_id = c.get('/auth/me', headers=courier).json()['id']
    assert c.post(f'/orders/{oid}/assign-courier-test', json={'courier_id': courier_id}, headers=farmer).status_code == 200
    assert c.get(f'/orders/{oid}/location', headers=courier).status_code == 403
    assert c.post(f'/orders/{oid}/dispatch-test', headers=farmer).status_code == 200
    assert c.get(f'/orders/{oid}/location', headers=courier).status_code == 200
    confirmed = c.post(f'/orders/{oid}/confirm', json={'pin': order['pin_test_only'], 'checked_goods': True}, headers=courier)
    assert confirmed.status_code == 200 and confirmed.json()['confirmed'] is True
    assert c.get(f'/orders/{oid}/location', headers=courier).status_code == 403
    assert c.get(f'/orders/{oid}/location', headers=buyer).status_code == 200
    assert c.get(f'/orders/{oid}/location', headers=farmer).status_code == 403
    assert c.get(f'/orders/{oid}/location', headers=other).status_code == 403

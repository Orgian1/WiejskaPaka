"""End-to-end SQLite regressions; no real payment provider or Neon connection."""
from tests.test_api import c, reg
from tests.test_stabilization_02 import _new_delivery


def test_delivery_end_to_end_privacy_and_one_time_pin():
    farmer, buyer, courier, other, order = _new_delivery('audit04-journey')
    oid = order['id']
    assert order['total_grosze'] == 1800
    courier_id = c.get('/auth/me', headers=courier).json()['id']
    assert c.post(f'/orders/{oid}/dispatch-test', headers=farmer).status_code == 409
    assert c.post(f'/orders/{oid}/assign-courier-test', headers=farmer,
                  json={'courier_id': courier_id}).status_code == 200
    assert c.get(f'/orders/{oid}/location', headers=courier).status_code == 403
    assert c.post(f'/orders/{oid}/dispatch-test', headers=farmer).status_code == 200
    assert c.post(f'/orders/{oid}/dispatch-test', headers=farmer).status_code == 409
    assert c.get(f'/orders/{oid}/location', headers=courier).status_code == 200
    assert c.get(f'/orders/{oid}/location', headers=other).status_code == 403
    assert c.post(f'/orders/{oid}/confirm', headers=other,
                  json={'pin': order['pin_test_only'], 'checked_goods': True}).status_code == 403
    assert c.post(f'/orders/{oid}/confirm', headers=courier,
                  json={'pin': order['pin_test_only'], 'checked_goods': False}).status_code == 422
    response = c.post(f'/orders/{oid}/confirm', headers=courier,
                      json={'pin': order['pin_test_only'], 'checked_goods': True})
    assert response.status_code == 200 and response.json()['confirmed']
    assert c.get(f'/orders/{oid}/location', headers=courier).status_code == 403
    assert c.post(f'/orders/{oid}/confirm', headers=courier,
                  json={'pin': order['pin_test_only'], 'checked_goods': True}).status_code == 409
    mine = c.get('/orders/me', headers=buyer)
    assert mine.status_code == 200
    assert any(x['id'] == oid and x['status'] == 'odebrane' for x in mine.json())


def test_pin_five_failures_lock_even_correct_pin():
    farmer, buyer, courier, other, order = _new_delivery('audit04-lock')
    oid = order['id']
    courier_id = c.get('/auth/me', headers=courier).json()['id']
    assert c.post(f'/orders/{oid}/assign-courier-test', headers=farmer,
                  json={'courier_id': courier_id}).status_code == 200
    assert c.post(f'/orders/{oid}/dispatch-test', headers=farmer).status_code == 200
    wrong = '000000' if order['pin_test_only'] != '000000' else '111111'
    for remaining in (4, 3, 2, 1, 0):
        result = c.post(f'/orders/{oid}/confirm', headers=courier,
                        json={'pin': wrong, 'checked_goods': True})
        assert result.status_code == 200
        assert result.json() == {'confirmed': False, 'remaining_attempts': remaining}
    assert c.post(f'/orders/{oid}/confirm', headers=courier,
                  json={'pin': order['pin_test_only'], 'checked_goods': True}).status_code == 409

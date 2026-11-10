"""Security and end-to-end regression tests for delivery-address access."""
from tests.test_api import c, reg


def _new_delivery(suffix):
    farmer = reg(f'farmer-security-{suffix}@example.org', 'rolnik')
    buyer = reg(f'buyer-security-{suffix}@example.org', 'klient')
    courier = reg(f'courier-security-{suffix}@example.org', 'dostawca')
    other = reg(f'other-security-{suffix}@example.org', 'dostawca')
    product = c.post('/products', json={
        'name': 'Marchew ekologiczna', 'price_grosze': 1299,
        'delivery_grosze': 501, 'stock': 2
    }, headers=farmer)
    assert product.status_code == 201, product.text
    order = c.post('/orders', json={
        'product_id': product.json()['id'], 'quantity': 1,
        'fulfillment': 'dostawa', 'delivery_city': 'Kraków',
        'delivery_street': 'Słoneczna 4', 'delivery_postal_code': '30-001'
    }, headers=buyer)
    assert order.status_code == 201, order.text
    return farmer, buyer, courier, other, order.json()


def test_courier_address_access_only_after_assignment():
    farmer, buyer, courier, other, order = _new_delivery('a')
    oid = order['id']
    endpoint = f'/orders/{oid}/location'
    assert c.get(endpoint, headers=courier).status_code == 403
    assert c.get(endpoint, headers=other).status_code == 403
    assert c.get(endpoint, headers=buyer).status_code == 200
    assert c.get(endpoint, headers=farmer).status_code == 403
    courier_id = c.get('/auth/me', headers=courier).json()['id']
    assert c.post(f'/orders/{oid}/assign-courier-test',
                  json={'courier_id': courier_id}, headers=farmer).status_code == 200
    assert c.get(endpoint, headers=courier).status_code == 403
    assert c.post(f'/orders/{oid}/dispatch-test', headers=farmer).status_code == 200
    result = c.get(endpoint, headers=courier)
    assert result.status_code == 200
    assert result.json() == {
        'fulfillment': 'dostawa', 'pickup_point_id': None,
        'delivery_city': 'Kraków', 'delivery_street': 'Słoneczna 4',
        'delivery_postal_code': '30-001'
    }
    assert c.get(endpoint, headers=other).status_code == 403
    assert 'email' not in result.text.lower()
    assert 'phone' not in result.text.lower()
    assert 'telefon' not in result.text.lower()


def test_assigned_courier_can_complete_delivery_and_pin_is_one_time():
    farmer, buyer, courier, other, order = _new_delivery('b')
    oid = order['id']
    courier_id = c.get('/auth/me', headers=courier).json()['id']
    assert c.post(f'/orders/{oid}/assign-courier-test',
                  json={'courier_id': courier_id}, headers=farmer).status_code == 200
    assert c.post(f'/orders/{oid}/dispatch-test', headers=farmer).status_code == 200
    assert c.get(f'/orders/{oid}/location', headers=courier).status_code == 200
    assert c.post(f'/orders/{oid}/confirm', json={
        'pin': '000000' if order['pin_test_only'] != '000000' else '111111',
        'checked_goods': True}, headers=courier).json()['confirmed'] is False
    good = c.post(f'/orders/{oid}/confirm', json={
        'pin': order['pin_test_only'], 'checked_goods': True}, headers=courier)
    assert good.status_code == 200 and good.json()['confirmed'] is True
    again = c.post(f'/orders/{oid}/confirm', json={
        'pin': order['pin_test_only'], 'checked_goods': True}, headers=courier)
    assert again.status_code == 409
    assert c.get(f'/orders/{oid}/events', headers=other).status_code == 403
    assert c.get(f'/orders/{oid}/events', headers=buyer).json()[-1]['new_status'] == 'odebrane'


def test_missing_order_location_and_no_auth():
    _, buyer, courier, _, order = _new_delivery('c')
    assert c.get('/orders/999999999/location', headers=buyer).status_code == 404
    assert c.get(f"/orders/{order['id']}/location").status_code == 401
    assert c.get(f"/orders/{order['id']}/location", headers=courier).status_code == 403


def test_pin_blocks_after_five_invalid_attempts():
    farmer, buyer, courier, _, order = _new_delivery('d')
    oid = order['id']
    courier_id = c.get('/auth/me', headers=courier).json()['id']
    assert c.post(f'/orders/{oid}/assign-courier-test', json={'courier_id': courier_id}, headers=farmer).status_code == 200
    assert c.post(f'/orders/{oid}/dispatch-test', headers=farmer).status_code == 200
    wrong = '000000' if order['pin_test_only'] != '000000' else '111111'
    for remaining in (4, 3, 2, 1, 0):
        response = c.post(f'/orders/{oid}/confirm', json={'pin': wrong, 'checked_goods': True}, headers=courier)
        assert response.status_code == 200
        assert response.json() == {'confirmed': False, 'remaining_attempts': remaining}
    assert c.post(f'/orders/{oid}/confirm', json={'pin': order['pin_test_only'], 'checked_goods': True}, headers=courier).status_code == 409


def test_order_location_other_buyer_is_forbidden():
    _, buyer, _, _, order = _new_delivery('e')
    stranger_buyer = reg('stranger-buyer-security-e@example.org', 'klient')
    assert c.get(f"/orders/{order['id']}/location", headers=stranger_buyer).status_code == 403
    assert c.get(f"/orders/{order['id']}/location", headers=buyer).status_code == 200


def test_delivery_cannot_be_confirmed_before_dispatch():
    farmer, buyer, courier, _, order = _new_delivery('f')
    oid = order['id']
    courier_id = c.get('/auth/me', headers=courier).json()['id']
    assert c.post(f'/orders/{oid}/assign-courier-test', json={'courier_id': courier_id}, headers=farmer).status_code == 200
    response = c.post(f'/orders/{oid}/confirm', json={'pin': order['pin_test_only'], 'checked_goods': True}, headers=courier)
    assert response.status_code == 409
    assert c.get(f'/orders/{oid}/location', headers=courier).status_code == 403

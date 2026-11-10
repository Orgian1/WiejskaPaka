"""Inventory conservation across successful, rejected and cancelled test orders."""
from uuid import uuid4
from tests.test_api import c, reg


def test_inventory_conservation_across_multiple_buyers_and_cancellation():
    tag = uuid4().hex[:10]
    farmer = reg(f'inv-f-{tag}@example.com', 'rolnik')
    buyers = [reg(f'inv-b-{i}-{tag}@example.com', 'klient') for i in range(3)]
    p = c.post('/products', json={'name': 'Marchew', 'price_grosze': 137, 'delivery_grosze': 23, 'stock': 5}, headers=farmer)
    assert p.status_code == 201
    pid = p.json()['id']
    point = c.post('/pickup-points', json={'name': 'Punkt', 'city': 'Radom', 'street': 'Polna 1', 'opening_hours': '8-16'}, headers=farmer)
    assert point.status_code == 201
    point_id = point.json()['id']

    def buy(who, qty):
        return c.post('/orders', json={'product_id': pid, 'quantity': qty, 'fulfillment': 'odbior', 'pickup_point_id': point_id}, headers=who)

    first = buy(buyers[0], 3)
    second = buy(buyers[1], 2)
    rejected = buy(buyers[2], 1)
    assert (first.status_code, second.status_code, rejected.status_code) == (201, 201, 409)
    assert first.json()['total_grosze'] == 411
    assert second.json()['total_grosze'] == 274

    def stock():
        response = c.get('/products/mine', headers=farmer)
        assert response.status_code == 200, response.text
        return next(item['stock'] for item in response.json() if item['id'] == pid)

    assert stock() == 0
    order_id = first.json()['id']
    cancel = c.post(f'/orders/{order_id}/cancel-test', headers=buyers[0])
    assert cancel.status_code == 200
    assert stock() == 3
    assert c.post(f'/orders/{order_id}/cancel-test', headers=buyers[0]).status_code == 409
    assert stock() == 3
    assert buy(buyers[2], 4).status_code == 409
    assert stock() == 3
    replacement = buy(buyers[2], 3)
    assert replacement.status_code == 201
    assert stock() == 0
    assert c.post(f'/orders/{replacement.json()["id"]}/cancel-test', headers=buyers[1]).status_code == 404
    assert stock() == 0

"""Regresja: dwaj klienci nie mogą kupić ostatniej sztuki jednocześnie."""
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4
from tests.test_api import c, reg


def test_parallel_buyers_do_not_oversell():
    suffix = uuid4().hex[:12]
    farmer = reg(f'parallel-farmer-{suffix}@example.com', 'rolnik')
    buyers = [reg(f'parallel-buyer-{i}-{suffix}@example.com', 'klient') for i in range(2)]
    product_response = c.post('/products', json={
        'name': 'Ostatnia sztuka', 'price_grosze': 101, 'delivery_grosze': 0, 'stock': 1
    }, headers=farmer)
    assert product_response.status_code == 201
    product_id = product_response.json()['id']
    point_response = c.post('/pickup-points', json={
        'name': 'Odbiór', 'city': 'Radom', 'street': 'Polna 1', 'opening_hours': '8-16'
    }, headers=farmer)
    assert point_response.status_code == 201
    point_id = point_response.json()['id']

    def purchase(headers):
        return c.post('/orders', json={
            'product_id': product_id, 'quantity': 1,
            'fulfillment': 'odbior', 'pickup_point_id': point_id
        }, headers=headers)

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(purchase, buyers))
    assert sorted(r.status_code for r in results) == [201, 409], [r.text for r in results]
    order_id = next(r.json()['id'] for r in results if r.status_code == 201)
    assert isinstance(order_id, int)
    assert c.post('/orders', json={
        'product_id': product_id, 'quantity': 1,
        'fulfillment': 'odbior', 'pickup_point_id': point_id
    }, headers=buyers[0]).status_code == 409

"""A 5 PLN product-only minimum is enforced server-side for every checkout path."""
from tests.test_local_marketplace import setup_market


def test_direct_checkout_minimum_ignores_delivery_fee():
    client, farmer, buyer, _, product, point, _ = setup_market()
    below = client.post('/orders', headers=buyer, json={
        'product_id': product, 'quantity': 1, 'fulfillment': 'dostawa',
        'delivery_city': 'Opole', 'delivery_street': 'Polna 1',
        'delivery_postal_code': '45-001'})
    assert below.status_code == 422
    assert '5,00 zł' in below.json()['detail']
    exact_or_more = client.post('/orders', headers=buyer, json={
        'product_id': product, 'quantity': 2, 'fulfillment': 'odbior',
        'pickup_point_id': point})
    assert exact_or_more.status_code == 201, exact_or_more.text
    assert exact_or_more.json()['subtotal_grosze'] == 598


def test_cart_checkout_minimum_checks_selected_seller_products():
    client, farmer, buyer, _, product, point, _ = setup_market()
    assert client.put('/cart/items', headers=buyer,
                      json={'product_id': product, 'quantity': 1}).status_code == 200
    payload = {'fulfillment': 'odbior', 'pickup_point_id': point}
    below = client.post('/cart/checkout-test', headers=buyer, json=payload)
    assert below.status_code == 422
    assert '5,00 zł' in below.json()['detail']
    assert client.put('/cart/items', headers=buyer,
                      json={'product_id': product, 'quantity': 2}).status_code == 200
    accepted = client.post('/cart/checkout-test', headers=buyer, json=payload)
    assert accepted.status_code == 201, accepted.text


def test_exact_500_groszy_is_accepted_and_499_rejected():
    client, farmer, buyer, _, product, point, _ = setup_market()
    for price, expected in ((499, 422), (500, 201)):
        changed = client.patch(f'/products/mine/{product}', headers=farmer,
                               json={'price_grosze': price})
        assert changed.status_code == 200, changed.text
        response = client.post('/orders', headers=buyer, json={
            'product_id': product, 'quantity': 1,
            'fulfillment': 'odbior', 'pickup_point_id': point})
        assert response.status_code == expected, response.text
        if expected == 201:
            assert response.json()['subtotal_grosze'] == 500

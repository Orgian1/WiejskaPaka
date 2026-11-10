"""Home delivery requires a positive shipment fee; pickup remains free."""
from fastapi.testclient import TestClient
from backend import app as api
from tests.test_b10921_security_boundaries import actor


def test_zero_delivery_rate_cannot_create_free_home_delivery():
    client = TestClient(api.app)
    farmer, _ = actor('rolnik')
    buyer, bid = actor('klient')
    pid = client.post('/products', headers=farmer, json={
        'name': 'Tylko odbiór', 'price_grosze': 100, 'delivery_grosze': 0, 'stock': 3}).json()['id']
    address = {'fulfillment': 'dostawa', 'delivery_city': 'Legnica',
               'delivery_street': 'Polna 1', 'delivery_postal_code': '59-220'}
    assert client.post('/orders', headers=buyer, json={**address, 'product_id': pid, 'quantity': 1}).status_code == 422
    assert client.post('/cart/quote', headers=buyer, json={
        'fulfillment': 'dostawa', 'items': [{'product_id': pid, 'quantity': 1}]}).status_code == 422
    assert client.put('/cart/items', headers=buyer, json={'product_id': pid, 'quantity': 1}).status_code == 200
    assert client.post('/cart/checkout-test', headers=buyer, json=address).status_code == 422
    with api.db() as con:
        assert con.execute('SELECT stock FROM products WHERE id=?', (pid,)).fetchone()['stock'] == 3
        assert con.execute('SELECT count(*) AS n FROM orders WHERE buyer_id=?', (bid,)).fetchone()['n'] == 0
        assert con.execute('SELECT count(*) AS n FROM saved_cart_items WHERE buyer_id=?', (bid,)).fetchone()['n'] == 1
    point = client.post('/pickup-points', headers=farmer, json={
        'name': 'Punkt', 'city': 'Legnica', 'street': 'Polna 1', 'opening_hours': '9:00–17:00'}).json()['id']
    response = client.post('/cart/checkout-test', headers=buyer,
                           json={'fulfillment': 'odbior', 'pickup_point_id': point})
    assert response.status_code == 201, response.text
    assert response.json()['delivery_grosze'] == 0


def test_one_positive_shipment_rate_covers_all_products_once():
    from backend.shipping_policy import shipment_fees
    items = [{'farmer_id': 1, 'delivery_grosze': 0}, {'farmer_id': 1, 'delivery_grosze': 1}]
    assert shipment_fees(items, 'dostawa') == {1: 1}

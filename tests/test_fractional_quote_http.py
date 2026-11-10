import uuid

import pytest
from fastapi.testclient import TestClient

from backend import app as module
from backend.product_unit_storage import SCHEMA_SQLITE


@pytest.fixture
def actors(monkeypatch):
    monkeypatch.setenv('WP_ENABLE_PRODUCT_UNITS', '1')
    monkeypatch.setenv('WP_ENABLE_FRACTIONAL_QUOTE', '1')
    with module.db() as con:
        con.executescript(SCHEMA_SQLITE)
    client = TestClient(module.app)
    headers = []
    for role in ('rolnik', 'klient'):
        data = {'email': uuid.uuid4().hex+'@example.invalid', 'role': role,
                'password': 'PrivateTestPassword2026'}
        assert client.post('/auth/register', json=data).status_code == 201
        login = client.post('/auth/login', json=data)
        assert login.status_code == 200
        headers.append({'Authorization': 'Bearer '+login.json()['access_token']})
    response = client.post('/products', headers=headers[0], json={
        'name': 'Jabłka na wagę', 'sale_unit': 'kg', 'stock': 10,
        'price_grosze': 201, 'delivery_grosze': 500})
    assert response.status_code == 201, response.text
    return client, *headers, response.json()['id']


def payload(pid, amount='0,5'):
    return {'items': [{'product_id': pid, 'quantity_text': amount}], 'fulfillment': 'dostawa'}


def test_fractional_quote_is_read_only_and_does_not_enable_checkout(actors):
    client, farmer, buyer, pid = actors
    def state():
        with module.db() as con:
            return (con.execute('SELECT stock FROM products WHERE id=?', (pid,)).fetchone()['stock'],
                    tuple(con.execute('SELECT COUNT(*) AS n FROM '+table).fetchone()['n']
                          for table in ('orders', 'inventory_reservations', 'saved_cart_items',
                                        'order_purchase_records', 'order_sale_units')))
    before = state()
    result = client.post('/cart/quote-quantities-test', headers=buyer, json=payload(pid))
    assert result.status_code == 200, result.text
    data = result.json()
    assert data['total_grosze'] == 601 and data['items'][0]['quantity_atoms'] == 500
    assert data['items'][0]['quantity_text'] == '0,5'
    assert data['checkout_supported'] is False
    assert state() == before
    config = client.get('/product-units').json()
    assert config['fractional_quote_enabled'] is True and config['fractional_quantities'] is False
    assert client.put('/cart/items', headers=buyer, json={'product_id': pid, 'quantity': 0.5}).status_code == 422
    assert client.post('/orders', headers=buyer, json={
        'product_id': pid, 'quantity': 0.5, 'fulfillment': 'dostawa',
        'delivery_city': 'Testowo', 'delivery_street': 'Polna 1', 'delivery_postal_code': '00-001'}).status_code == 422
    assert state() == before


@pytest.mark.parametrize('flag', ['WP_ENABLE_PRODUCT_UNITS', 'WP_ENABLE_FRACTIONAL_QUOTE'])
def test_both_flags_are_required(actors, monkeypatch, flag):
    client, _, buyer, pid = actors
    monkeypatch.delenv(flag)
    assert client.post('/cart/quote-quantities-test', headers=buyer, json=payload(pid)).status_code == 503
    assert client.get('/product-units').json()['fractional_quote_enabled'] is False


def test_only_authenticated_buyers_can_quote(actors):
    client, farmer, _, pid = actors
    assert client.post('/cart/quote-quantities-test', json=payload(pid)).status_code == 401
    assert client.post('/cart/quote-quantities-test', headers=farmer, json=payload(pid)).status_code == 403


def test_unavailable_and_invalid_quantities(actors):
    client, _, buyer, pid = actors
    for value in (0.5, True, '1e2', '-1', '0', '0.0001', '1000.001'):
        assert client.post('/cart/quote-quantities-test', headers=buyer, json=payload(pid, value)).status_code == 422
    assert client.post('/cart/quote-quantities-test', headers=buyer, json=payload(pid, '10.001')).status_code == 409

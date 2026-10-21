"""New sale-unit contract on the real application and isolated SQLite DB."""
import uuid

import pytest
from fastapi.testclient import TestClient
from backend import app as module
from backend.product_unit_storage import SCHEMA_SQLITE


@pytest.fixture
def actors(monkeypatch):
    monkeypatch.setenv('WP_ENABLE_PRODUCT_UNITS', '1')
    with module.db() as con:
        con.executescript(SCHEMA_SQLITE)
    client = TestClient(module.app)
    headers = []
    for role in ('rolnik', 'klient'):
        email = f'{uuid.uuid4().hex}@example.invalid'
        data = {'email': email, 'password': 'PrivateTestPassword2026', 'role': role}
        assert client.post('/auth/register', json=data).status_code == 201
        reply = client.post('/auth/login', json=data)
        assert reply.status_code == 200
        headers.append({'Authorization': 'Bearer ' + reply.json()['access_token']})
    return client, *headers


def listing(**changes):
    return {'name': 'Ziemniaki testowe', 'stock': 10, 'price_grosze': 200,
            'delivery_grosze': 500, 'sale_unit': 'kg', **changes}


def test_units_survive_catalog_cart_quote_and_order_record(actors):
    client, farmer, buyer = actors
    response = client.post('/products', headers=farmer, json=listing())
    assert response.status_code == 201, response.text
    product_id = response.json()['id']
    assert client.get(f'/products/{product_id}').json()['sale_unit'] == 'kg'
    assert any(p['id'] == product_id and p['sale_unit'] == 'kg'
               for p in client.get('/products/mine', headers=farmer).json())
    result = client.get('/catalog/search', params={'q': 'Ziemniaki testowe'}).json()
    assert next(p for p in result['items'] if p['id'] == product_id)['sale_unit'] == 'kg'
    assert client.put('/cart/items', headers=buyer, json={'product_id':product_id, 'quantity':2}).status_code == 200
    item = client.get('/cart/items', headers=buyer).json()['items'][0]
    assert item['sale_unit'] == 'kg' and item['quantity'] == 2
    quote = client.post('/cart/quote', headers=buyer, json={
        'items':[{'product_id':product_id,'quantity':2}], 'fulfillment':'dostawa'}).json()
    assert quote['items'][0]['sale_unit'] == 'kg'
    assert quote['subtotal_grosze'] == 400 and quote['delivery_grosze'] == 500
    order = client.post('/orders', headers=buyer, json={
        'product_id':product_id,'quantity':2,'fulfillment':'dostawa',
        'delivery_city':'Testowo','delivery_street':'Polna 1','delivery_postal_code':'00-001'})
    assert order.status_code == 201, order.text
    with module.db() as con:
        saved = con.execute('SELECT unit FROM order_sale_units WHERE order_id=?',(order.json()['id'],)).fetchone()
        assert saved['unit'] == 'kg'
        assert con.execute('SELECT stock FROM products WHERE id=?',(product_id,)).fetchone()['stock'] == 8


def test_packaging_requires_content_and_returns_it(actors):
    client, farmer, _ = actors
    assert client.post('/products', headers=farmer, json=listing(sale_unit='worek')).status_code == 422
    result = client.post('/products', headers=farmer, json=listing(
        sale_unit='worek',content_amount='15',content_unit='kg'))
    assert result.status_code == 201
    assert client.get('/products/'+str(result.json()['id'])).json()['package_content'] == {
        'amount_atoms':15000,'unit':'kg'}


def test_disabled_feature_rejects_non_piece_listing(actors,monkeypatch):
    client, farmer, _ = actors
    monkeypatch.delenv('WP_ENABLE_PRODUCT_UNITS')
    assert client.post('/products', headers=farmer, json=listing()).status_code == 503
    assert client.get('/product-units').json()['enabled'] is False


def test_fractional_contract_is_not_advertised_as_enabled(actors):
    client, farmer, _ = actors
    config = client.get('/product-units').json()
    assert len(config['units']) == 12 and config['fractional_quantities'] is False
    assert client.post('/products', headers=farmer,json=listing(stock=0.5)).status_code == 422


def test_unit_cannot_be_edited_after_creation(actors):
    client, farmer, _ = actors
    product_id = client.post('/products', headers=farmer, json=listing()).json()['id']
    result = client.patch(f'/products/mine/{product_id}', headers=farmer, json={'sale_unit':'szt'})
    assert result.status_code == 422
    assert client.get(f'/products/{product_id}').json()['sale_unit'] == 'kg'


def test_restart_cannot_silently_relabel_kilograms_as_pieces(actors,monkeypatch):
    client, farmer, _ = actors
    assert client.post('/products', headers=farmer, json=listing()).status_code == 201
    monkeypatch.delenv('WP_ENABLE_PRODUCT_UNITS')
    with pytest.raises(RuntimeError, match='Nie można wyłączyć jednostek'):
        with TestClient(module.app):
            pass


def test_enabled_restart_keeps_listing_and_purchase_unit(actors):
    client, farmer, buyer = actors
    product = client.post('/products', headers=farmer, json=listing(
        sale_unit='butelka', content_amount='0,75', content_unit='l'))
    assert product.status_code == 201, product.text
    product_id = product.json()['id']
    order = client.post('/orders', headers=buyer, json={
        'product_id': product_id, 'quantity': 2, 'fulfillment': 'dostawa',
        'delivery_city': 'Testowo', 'delivery_street': 'Polna 1',
        'delivery_postal_code': '00-001',
    })
    assert order.status_code == 201, order.text
    record_url = f"/orders/{order.json()['id']}/purchase-record"
    original = client.get(record_url, headers=buyer).json()['original']
    # Enter the actual application lifespan again, keeping the persisted DB.
    with TestClient(module.app) as restarted:
        listing_after = restarted.get(f'/products/{product_id}').json()
        assert listing_after['sale_unit'] == 'butelka'
        assert listing_after['package_content'] == {'amount_atoms': 750, 'unit': 'l'}
        assert listing_after['stock'] == 8
        assert restarted.get(record_url, headers=buyer).json()['original'] == original


@pytest.mark.parametrize('unit', [
    'szt', 'kg', 'g', 'l', 'ml', 'opak', 'peczek', 'sloik',
    'butelka', 'worek', 'skrzynka', 'tacka',
])
def test_every_unit_keeps_purchase_terms_and_restores_stock_once(actors, unit):
    client, farmer, buyer = actors
    packaged = unit in {'opak', 'sloik', 'butelka', 'worek', 'skrzynka', 'tacka'}
    content = {'content_amount': '0,75', 'content_unit': 'kg'} if packaged else {}
    created = client.post('/products', headers=farmer,
                          json=listing(sale_unit=unit, **content))
    assert created.status_code == 201, created.text
    product_id = created.json()['id']
    ordered = client.post('/orders', headers=buyer, json={
        'product_id': product_id, 'quantity': 3, 'fulfillment': 'dostawa',
        'delivery_city': 'Testowo', 'delivery_street': 'Polna 1',
        'delivery_postal_code': '00-001',
    })
    assert ordered.status_code == 201, ordered.text
    order_id = ordered.json()['id']
    record_url = f'/orders/{order_id}/purchase-record'
    before = client.get(record_url, headers=buyer)
    assert before.status_code == 200, before.text
    original = before.json()['original']
    assert original['product']['sale_unit'] == unit
    assert original['product']['package_content'] == (
        {'amount_atoms': 750, 'unit': 'kg'} if packaged else None)
    assert original['quantity'] == 3
    assert original['subtotal_grosze'] == 600
    assert original['delivery_grosze'] == 500
    assert original['total_grosze'] == 1100
    changed = client.patch(f'/products/mine/{product_id}', headers=farmer,
                           json={'name': 'Zmieniona oferta', 'price_grosze': 999})
    assert changed.status_code == 200, changed.text
    assert client.get(record_url, headers=farmer).json()['original'] == original
    cancelled = client.post(f'/orders/{order_id}/cancel-test', headers=buyer)
    assert cancelled.status_code == 200, cancelled.text
    assert client.get(f'/products/{product_id}').json()['stock'] == 10
    assert client.post(f'/orders/{order_id}/cancel-test', headers=buyer).status_code == 409
    assert client.get(f'/products/{product_id}').json()['stock'] == 10
    assert client.get(record_url, headers=buyer).json()['original'] == original

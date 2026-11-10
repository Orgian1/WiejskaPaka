"""B/66–70: real FastAPI authorization checks on isolated SQLite."""
import uuid
import pytest
from fastapi.testclient import TestClient
from backend.app import app



def account(client, role):
    n = uuid.uuid4().hex
    email = f'iso-b70-{n}-{role}@example.test'
    payload = {'email': email, 'password': 'bezpieczne-haslo-testowe-2026', 'role': role}
    assert client.post('/auth/register', json=payload).status_code == 201
    response = client.post('/auth/login', json={'email': email, 'password': payload['password']})
    assert response.status_code == 200
    return {'Authorization': f"Bearer {response.json()['access_token']}"}


@pytest.fixture
def scenario():
    with TestClient(app) as client:
        farmer = account(client, 'rolnik')
        stranger = account(client, 'rolnik')
        buyer = account(client, 'klient')
        another_buyer = account(client, 'klient')
        courier = account(client, 'dostawca')
        product = client.post('/products', headers=farmer, json={
            'name': 'Test izolacji kont', 'price_grosze': 349,
            'delivery_grosze': 501, 'stock': 10})
        assert product.status_code == 201, product.text
        point = client.post('/pickup-points', headers=farmer, json={
            'name': 'Punkt testowy', 'city': 'Radom', 'street': 'Polna 2',
            'opening_hours': '8-16'})
        assert point.status_code == 201, point.text
        order = client.post('/orders', headers=buyer, json={
            'product_id': product.json()['id'], 'quantity': 1,
            'fulfillment': 'odbior', 'pickup_point_id': point.json()['id']})
        assert order.status_code == 201, order.text
        yield client, farmer, stranger, buyer, another_buyer, courier, order.json()['id']


def test_b66_farmer_cannot_read_other_farmers_orders(scenario):
    c, farmer, stranger, *_ = scenario
    assert any(row['id'] == scenario[-1] for row in c.get('/orders/me', headers=farmer).json())
    assert all(row['id'] != scenario[-1] for row in c.get('/orders/me', headers=stranger).json())


def test_b67_buyer_cannot_read_other_buyers_orders(scenario):
    c, _, _, buyer, another, _, order_id = scenario
    assert any(row['id'] == order_id for row in c.get('/orders/me', headers=buyer).json())
    assert all(row['id'] != order_id for row in c.get('/orders/me', headers=another).json())


def test_b68_other_buyer_cannot_read_order_location(scenario):
    c, _, _, buyer, another, _, order_id = scenario
    assert c.get(f'/orders/{order_id}/location', headers=buyer).status_code == 200
    assert c.get(f'/orders/{order_id}/location', headers=another).status_code == 403


def test_b69_unassigned_courier_cannot_read_location_or_events(scenario):
    c, _, _, _, _, courier, order_id = scenario
    assert c.get(f'/orders/{order_id}/location', headers=courier).status_code == 403
    assert c.get(f'/orders/{order_id}/events', headers=courier).status_code == 403
    assert all(row['id'] != order_id for row in c.get('/couriers/me/orders', headers=courier).json())


def test_b70_other_farmer_cannot_modify_order_or_view_events(scenario):
    c, _, stranger, _, _, _, order_id = scenario
    assert c.get(f'/orders/{order_id}/events', headers=stranger).status_code == 403
    assert c.post(f'/test/orders/{order_id}/ready', headers=stranger).status_code in (403, 404)
    assert c.post(f'/orders/{order_id}/confirm', headers=stranger,
                  json={'pin': '000000', 'checked_goods': True}).status_code == 403

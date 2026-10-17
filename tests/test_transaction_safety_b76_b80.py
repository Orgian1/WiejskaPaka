"""B/76–80: atomicity, validation and session revocation through actual FastAPI endpoints."""
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4
from fastapi.testclient import TestClient
from backend.app import app


def actor(c, role):
    email = f'b80-{uuid4().hex}@example.test'
    password = 'test-password-2026-strong'
    assert c.post('/auth/register', json={'email': email, 'password': password, 'role': role}).status_code == 201
    response = c.post('/auth/login', json={'email': email, 'password': password})
    assert response.status_code == 200
    return {'Authorization': 'Bearer ' + response.json()['access_token']}


def fixture(stock=3):
    c = TestClient(app)
    farmer, buyer, stranger = actor(c, 'rolnik'), actor(c, 'klient'), actor(c, 'klient')
    product = c.post('/products', headers=farmer, json={'name': 'Test atomowosci', 'price_grosze': 349, 'delivery_grosze': 501, 'stock': stock})
    assert product.status_code == 201, product.text
    point = c.post('/pickup-points', headers=farmer, json={'name': 'Odbior', 'city': 'Radom', 'street': 'Polna 1', 'opening_hours': '8-16'})
    assert point.status_code == 201, point.text
    return c, farmer, buyer, stranger, product.json()['id'], point.json()['id']


def available(c, product_id):
    return next(p['stock'] for p in c.get('/products').json() if p['id'] == product_id)


def pickup(product_id, point_id, **kw):
    return {'product_id': product_id, 'quantity': 1, 'fulfillment': 'odbior', 'pickup_point_id': point_id, **kw}


def test_b76_invalid_pickup_does_not_reduce_stock():
    c, f, b, s, pid, point = fixture()
    before = available(c, pid)
    result = c.post('/orders', headers=b, json=pickup(pid, point + 999999))
    assert result.status_code == 422, result.text
    assert available(c, pid) == before
    assert c.get('/orders/me', headers=b).json() == []


def test_b77_invalid_delivery_does_not_create_order():
    c, f, b, s, pid, point = fixture()
    result = c.post('/orders', headers=b, json={'product_id': pid, 'quantity': 1, 'fulfillment': 'dostawa', 'delivery_city': 'Radom', 'delivery_street': 'Polna 1'})
    assert result.status_code == 422, result.text
    assert available(c, pid) == 3
    assert c.get('/orders/me', headers=b).json() == []


def test_b78_failed_purchase_does_not_block_next_valid_purchase():
    c, f, b, s, pid, point = fixture(stock=1)
    assert c.post('/orders', headers=b, json=pickup(pid, point + 999999)).status_code == 422
    valid = c.post('/orders', headers=b, json=pickup(pid, point))
    assert valid.status_code == 201, valid.text
    assert not any(p['id'] == pid for p in c.get('/products').json())
    assert len(c.get('/orders/me', headers=b).json()) == 1


def test_b79_revoked_session_cannot_place_order():
    c, f, b, s, pid, point = fixture()
    assert c.post('/auth/logout', headers=b).status_code == 200
    result = c.post('/orders', headers=b, json=pickup(pid, point))
    assert result.status_code in (401, 403), result.text
    assert available(c, pid) == 3


def test_b80_concurrent_invalid_and_valid_orders_preserve_stock():
    c, f, b, s, pid, point = fixture(stock=1)
    requests = [(b, pickup(pid, point)), (s, pickup(pid, point + 999999))]
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(lambda item: c.post('/orders', headers=item[0], json=item[1]), requests))
    assert responses[0].status_code == 201 and responses[1].status_code in (409, 422), [r.text for r in responses]
    assert len(c.get('/orders/me', headers=b).json()) == 1
    assert c.get('/orders/me', headers=s).json() == []

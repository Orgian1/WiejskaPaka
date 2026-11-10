"""B/91–B/95: public/private HTTP boundaries and malformed requests."""
from uuid import uuid4
from fastapi.testclient import TestClient
from backend.app import app, db


def test_b91_private_error_responses_are_not_cached():
    c = TestClient(app)
    for path in ('/orders/me', '/couriers/me/orders', '/auth/me'):
        response = c.get(path)
        assert response.status_code == 401
        assert response.headers['cache-control'] == 'no-store'
        assert response.headers['pragma'] == 'no-cache'


def test_b92_security_headers_cover_validation_errors():
    c = TestClient(app)
    response = c.post('/auth/register', json={})
    assert response.status_code == 422
    assert response.headers['cache-control'] == 'no-store'
    assert response.headers['x-frame-options'] == 'DENY'
    assert response.headers['referrer-policy'] == 'no-referrer'
    assert "frame-ancestors 'none'" in response.headers['content-security-policy']


def test_b93_anonymous_order_rejected_before_payload_processing():
    c = TestClient(app)
    response = c.post('/orders', json={'product_id': 1, 'quantity': 1, 'fulfillment': 'dostawa', 'delivery_city': 'Test', 'delivery_street': 'Test 1', 'delivery_postal_code': '00-001'})
    assert response.status_code == 401
    assert response.headers['cache-control'] == 'no-store'


def test_b94_invalid_login_does_not_create_session():
    c = TestClient(app)
    email = f'b94-{uuid4().hex}@example.test'
    response = c.post('/auth/login', json={'email': email, 'password': 'invalid-password'})
    assert response.status_code == 401
    with db() as con:
        assert con.execute('SELECT COUNT(*) AS n FROM sessions s JOIN users u ON s.user_id=u.id WHERE u.email=?', (email,)).fetchone()['n'] == 0


def test_b95_public_catalog_has_no_private_user_data():
    c = TestClient(app)
    response = c.get('/products')
    assert response.status_code == 200
    assert response.headers['cache-control'] == 'no-cache'
    for item in response.json():
        assert set(item) == {'id', 'farmer_id', 'name', 'price_grosze', 'delivery_grosze', 'stock'}
        assert not any(k in item for k in ('email', 'phone', 'delivery_street', 'pin_hash'))

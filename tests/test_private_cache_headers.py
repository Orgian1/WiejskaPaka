"""Ochrona prywatnych odpowiedzi HTTP przed cache po wylogowaniu."""
from fastapi.testclient import TestClient
from backend.app import app


def test_private_endpoints_never_cache_even_when_unauthorized():
    client = TestClient(app)
    for path in ('/auth/me', '/orders/me', '/farmers/me/profile',
                 '/couriers/me/orders', '/couriers/me/active-addresses',
                 '/products/mine', '/notifications/me',
                 '/accounting/commission-drafts/me',
                 '/test/farmers/me/payout-report',
                 '/marketplace/orders/999/settlement-preview'):
        response = client.get(path)
        assert response.headers['cache-control'] == 'no-store', path
        assert response.headers['x-content-type-options'] == 'nosniff'
        assert response.headers['x-frame-options'] == 'DENY'


def test_public_catalog_retains_separate_cache_policy():
    client = TestClient(app)
    response = client.get('/')
    assert response.status_code == 200
    assert response.headers['cache-control'] == 'no-cache'


def test_private_admin_and_mutating_routes_default_to_no_store():
    client = TestClient(app)
    for path in ('/admin/farmers/1/compliance/review', '/pickup-points',
                 '/notifications/1/read', '/products', '/orders',
                 '/not-yet-existing-private-route'):
        response = client.post(path, json={})
        assert response.headers['cache-control'] == 'no-store', path
        assert response.headers['pragma'] == 'no-cache', path


def test_public_exact_match_does_not_expose_similar_private_path():
    client = TestClient(app)
    for path in ('/products/mine', '/marketplace/orders/1/settlement-preview',
                 '/health/private', '/admin/farmers/1/compliance/review'):
        response = client.get(path)
        assert response.headers['cache-control'] == 'no-store', path
    assert client.get('/products').headers['cache-control'] == 'no-cache'
    assert client.get('/health').headers['cache-control'] == 'no-cache'

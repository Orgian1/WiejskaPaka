"""Sprawdza ograniczenia wycieku danych i dostępu do funkcji urządzenia."""
from fastapi.testclient import TestClient
from backend.app import app


def test_security_headers_on_public_and_private_responses():
    client = TestClient(app)
    for path in ('/', '/products', '/auth/me', '/couriers/me/active-addresses', '/missing-private'):
        response = client.get(path)
        assert response.headers['referrer-policy'] == 'no-referrer', path
        permissions = response.headers['permissions-policy']
        for capability in ('camera=()', 'microphone=()', 'geolocation=(self)', 'payment=()'):
            assert capability in permissions, path
        csp = response.headers['content-security-policy']
        for directive in ("connect-src 'self'", "form-action 'self'", "frame-ancestors 'none'"):
            assert directive in csp, path


def test_unknown_private_route_not_cached_even_on_error():
    response = TestClient(app).get('/not-existing-sensitive-resource')
    assert response.status_code == 404
    assert response.headers['cache-control'] == 'no-store'
    assert response.headers['pragma'] == 'no-cache'

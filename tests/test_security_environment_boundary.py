"""Production rejection cannot depend on the simulated-payment switch."""
import pytest
from fastapi.testclient import TestClient
from backend.app import app

@pytest.mark.parametrize('mode', ['production', ' PROD ', 'live', 'unknown'])
@pytest.mark.parametrize('payments', ['0', '1'])
def test_all_routes_fail_closed_after_environment_change(monkeypatch, mode, payments):
    # No lifespan: emulate an already running worker whose environment changes.
    client = TestClient(app)
    monkeypatch.setenv('WP_ENV', mode)
    monkeypatch.setenv('WP_ENABLE_TEST_PAYMENTS', payments)
    for route in app.routes:
        for method in getattr(route, 'methods', set()) - {'HEAD', 'OPTIONS'}:
            response = client.request(method, route.path)
            assert response.status_code == 503, (method, route.path, response.text)
            assert response.headers['cache-control'] == 'no-store'
            assert response.json() == {'detail': 'Środowisko niedozwolone'}

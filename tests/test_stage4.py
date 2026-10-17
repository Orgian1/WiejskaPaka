from fastapi.testclient import TestClient
from backend.app import app

def test_catalog_has_farmer_id():
    with TestClient(app) as client:
        r=client.get('/products')
        assert r.status_code == 200
        assert all('farmer_id' in p for p in r.json())

def test_private_pickup_endpoint_requires_login():
    with TestClient(app) as client:
        assert client.get('/farmers/me/pickup-points').status_code == 401

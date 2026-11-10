"""B/81–85: regression checks for revoked credentials and cross-account access."""
from uuid import uuid4
from fastapi.testclient import TestClient
from backend.app import app


def create_actor(client, role='klient'):
    email = f'b85-{uuid4().hex}@example.test'
    password = 'safe-pass-2026-123'
    assert client.post('/auth/register', json={'email': email, 'password': password, 'role': role}).status_code == 201
    login = client.post('/auth/login', json={'email': email, 'password': password})
    assert login.status_code == 200, login.text
    return email, password, {'Authorization': 'Bearer ' + login.json()['access_token']}


def test_b81_logout_all_revokes_multiple_sessions():
    c = TestClient(app)
    email, password, first = create_actor(c)
    second_login = c.post('/auth/login', json={'email': email, 'password': password})
    assert second_login.status_code == 200
    second = {'Authorization': 'Bearer ' + second_login.json()['access_token']}
    assert c.get('/orders/me', headers=second).status_code == 200
    assert c.post('/auth/logout-all', headers=first).status_code == 200
    assert c.get('/orders/me', headers=first).status_code == 401
    assert c.get('/orders/me', headers=second).status_code == 401


def test_b82_logout_only_revokes_current_session():
    c = TestClient(app)
    email, password, first = create_actor(c)
    second_login = c.post('/auth/login', json={'email': email, 'password': password})
    second = {'Authorization': 'Bearer ' + second_login.json()['access_token']}
    assert c.post('/auth/logout', headers=first).status_code == 200
    assert c.get('/orders/me', headers=first).status_code == 401
    assert c.get('/orders/me', headers=second).status_code == 200


def test_b83_revoked_token_cannot_log_out_other_sessions():
    c = TestClient(app)
    email, password, first = create_actor(c)
    assert c.post('/auth/logout', headers=first).status_code == 200
    assert c.post('/auth/logout-all', headers=first).status_code == 401
    fresh = c.post('/auth/login', json={'email': email, 'password': password})
    assert fresh.status_code == 200
    assert c.get('/orders/me', headers={'Authorization': 'Bearer ' + fresh.json()['access_token']}).status_code == 200


def test_b84_unauthenticated_session_mutations_are_rejected():
    c = TestClient(app)
    assert c.post('/auth/logout').status_code == 401
    assert c.post('/auth/logout-all').status_code == 401
    assert c.get('/orders/me').status_code == 401


def test_b85_courier_cannot_read_buyer_order_history():
    c = TestClient(app)
    _, _, courier = create_actor(c, 'dostawca')
    _, _, buyer = create_actor(c, 'klient')
    assert c.get('/orders/me', headers=buyer).status_code == 200
    assert c.get('/orders/me', headers=courier).status_code == 403

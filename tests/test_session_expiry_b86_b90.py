"""B/86–90: expiry and token-boundary integration checks on isolated SQLite."""
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from fastapi.testclient import TestClient
from backend.app import app, db, token_hash


def actor(client):
    email = f'b90-{uuid4().hex}@example.test'
    password = 'safe-pass-2026-123'
    assert client.post('/auth/register', json={'email': email, 'password': password, 'role': 'klient'}).status_code == 201
    result = client.post('/auth/login', json={'email': email, 'password': password})
    assert result.status_code == 200
    return result.json()['access_token']


def headers(token):
    return {'Authorization': f'Bearer {token}'}


def test_b86_expired_session_cannot_read_orders():
    c = TestClient(app)
    token = actor(c)
    with db() as con:
        con.execute('UPDATE sessions SET expires_at=? WHERE token_hash=?', ((datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat(), token_hash(token)))
    assert c.get('/orders/me', headers=headers(token)).status_code == 401


def test_b87_expired_session_cannot_logout_all():
    c = TestClient(app)
    token = actor(c)
    with db() as con:
        con.execute('UPDATE sessions SET expires_at=? WHERE token_hash=?', ((datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat(), token_hash(token)))
    assert c.post('/auth/logout-all', headers=headers(token)).status_code == 401


def test_b88_malformed_authorization_headers_rejected():
    c = TestClient(app)
    token = actor(c)
    for value in (token, f'bearer {token}', f'Basic {token}', 'Bearer ', f'Bearer {token}extra'):
        assert c.get('/orders/me', headers={'Authorization': value}).status_code == 401
    assert c.get('/orders/me', headers=headers(token)).status_code == 200


def test_b89_login_after_expiry_creates_fresh_session():
    c = TestClient(app)
    email = f'b90-{uuid4().hex}@example.test'
    password = 'safe-pass-2026-123'
    assert c.post('/auth/register', json={'email': email, 'password': password, 'role': 'klient'}).status_code == 201
    first = c.post('/auth/login', json={'email': email, 'password': password}).json()['access_token']
    with db() as con:
        con.execute('UPDATE sessions SET expires_at=? WHERE token_hash=?', ((datetime.now(timezone.utc) - timedelta(days=1)).isoformat(), token_hash(first)))
    second = c.post('/auth/login', json={'email': email, 'password': password}).json()['access_token']
    assert first != second
    assert c.get('/orders/me', headers=headers(first)).status_code == 401
    assert c.get('/orders/me', headers=headers(second)).status_code == 200


def test_b90_revoked_token_not_reactivated_by_new_login():
    c = TestClient(app)
    email = f'b90-{uuid4().hex}@example.test'
    password = 'safe-pass-2026-123'
    assert c.post('/auth/register', json={'email': email, 'password': password, 'role': 'klient'}).status_code == 201
    old = c.post('/auth/login', json={'email': email, 'password': password}).json()['access_token']
    assert c.post('/auth/logout', headers=headers(old)).status_code == 200
    new = c.post('/auth/login', json={'email': email, 'password': password}).json()['access_token']
    assert c.get('/orders/me', headers=headers(old)).status_code == 401
    assert c.get('/orders/me', headers=headers(new)).status_code == 200

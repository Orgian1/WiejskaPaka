"""Adversarial API regressions; run on a disposable SQLite database."""
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from backend import app as api


@pytest.fixture
def client():
    return TestClient(api.app)


def actor(role, expiry=None):
    token = uuid4().hex
    with api.db() as con:
        uid = con.execute('INSERT INTO users(email,password_hash,role) VALUES(?,?,?)',
                          (token + '@example.invalid', 'unused', role)).lastrowid
        con.execute('INSERT INTO sessions(token_hash,user_id,expires_at) VALUES(?,?,?)',
                    (api.token_hash(token), uid, expiry or
                     (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()))
    return {'Authorization': 'Bearer ' + token}, uid


@pytest.mark.parametrize('kind', ['expired_offset', 'future_offset', 'naive', 'invalid'])
def test_session_expiry_is_parsed_as_an_instant(client, kind):
    now = datetime.now(timezone.utc)
    expiry = {
        'expired_offset': (now - timedelta(minutes=5)).astimezone(timezone(timedelta(hours=14))).isoformat(),
        'future_offset': (now + timedelta(minutes=5)).astimezone(timezone(-timedelta(hours=12))).isoformat(),
        'naive': (now + timedelta(days=1)).replace(tzinfo=None).isoformat(),
        'invalid': 'zzzz-not-a-date',
    }[kind]
    headers, _ = actor('klient', expiry)
    assert client.get('/auth/me', headers=headers).status_code == (200 if kind == 'future_offset' else 401)


@pytest.mark.parametrize('field,value', [('email', 'x' * 255), ('password', 'x' * 257)])
def test_login_has_bounded_inputs(client, field, value):
    body = {'email': 'unknown@example.invalid', 'password': 'not-a-password'}
    body[field] = value
    assert client.post('/auth/login', json=body).status_code == 422


@pytest.mark.parametrize('field', ['price_grosze', 'delivery_grosze', 'stock'])
@pytest.mark.parametrize('value', [True, 1.0, 1.5, '100'])
def test_product_integer_fields_reject_coercion(client, field, value):
    headers, _ = actor('rolnik')
    body = {'name': 'Marchew', 'price_grosze': 100, 'delivery_grosze': 100, 'stock': 10}
    body[field] = value
    assert client.post('/products', headers=headers, json=body).status_code == 422


@pytest.mark.parametrize('path,body', [
    ('/products', {'name': '  ', 'price_grosze': 100, 'delivery_grosze': 100, 'stock': 10}),
    ('/pickup-points', {'name': 'Punkt', 'city': '  ', 'street': '   ', 'opening_hours': '   '}),
    ('/farmers/me/profile', {'farm_name': '  ', 'city': '  '}),
])
def test_blank_listing_fields_rejected_before_save(client, path, body):
    headers, _ = actor('rolnik')
    method = client.put if path.endswith('/profile') else client.post
    assert method(path, headers=headers, json=body).status_code == 422


def test_blank_delivery_address_does_not_reserve_stock(client):
    farmer, fid = actor('rolnik')
    buyer, bid = actor('klient')
    product = client.post('/products', headers=farmer, json={
        'name': 'Ziemniaki', 'price_grosze': 199, 'delivery_grosze': 500, 'stock': 3}).json()['id']
    response = client.post('/orders', headers=buyer, json={
        'product_id': product, 'quantity': 1, 'fulfillment': 'dostawa',
        'delivery_city': '  ', 'delivery_street': '   ', 'delivery_postal_code': '59-500'})
    assert response.status_code == 422
    with api.db() as con:
        assert con.execute('SELECT stock FROM products WHERE id=?', (product,)).fetchone()['stock'] == 3
        assert con.execute('SELECT COUNT(*) AS n FROM orders WHERE buyer_id=?', (bid,)).fetchone()['n'] == 0


def test_invalid_body_never_echoes_password(client):
    password = 'private-test-value-do-not-echo'
    response = client.post('/auth/register', json={'email': 'x', 'password': password, 'role': 'admin'})
    assert response.status_code == 422
    assert password not in response.text
    assert 'input' not in response.json()['detail'][0]


def test_expired_lockout_starts_new_attempt_window(client):
    email = uuid4().hex + '@example.invalid'
    with api.db() as con:
        con.execute('INSERT INTO login_attempts(email,failures,locked_until) VALUES(?,?,?)',
                    (email, 5, (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()))
    for _ in range(2):
        assert client.post('/auth/login', json={'email': email, 'password': 'wrong'}).status_code == 401
    with api.db() as con:
        row = con.execute('SELECT failures,locked_until FROM login_attempts WHERE email=?', (email,)).fetchone()
        assert row['failures'] == 2 and row['locked_until'] is None

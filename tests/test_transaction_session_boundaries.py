"""A dependency snapshot is insufficient authorization for a later DB write."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import hashlib
import json
from threading import Event

from fastapi import Header, Request
from fastapi.testclient import TestClient
import pytest

from backend import app as api
from tests.test_b10921_security_boundaries import actor


def database_digest():
    digest = hashlib.sha256()
    with api.db() as con:
        names = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
        for name in names:
            quoted = '"' + name.replace('"', '""') + '"'
            rows = sorted(json.dumps(list(row), default=str, ensure_ascii=True)
                          for row in con.execute('SELECT * FROM ' + quoted))
            digest.update(json.dumps([name, rows]).encode('utf-8'))
    return digest.hexdigest()


def scenario(name):
    client = TestClient(api.app)
    farmer, fid = actor('rolnik')
    buyer, bid = actor('klient')
    point_body = {'name': 'Punkt testowy', 'city': 'Opole', 'street': 'Testowa 1', 'opening_hours': '9-17'}
    point = client.post('/pickup-points', headers=farmer, json=point_body).json()['id']
    product_body = {'name': 'Testowe jabłka', 'price_grosze': 199, 'delivery_grosze': 501, 'stock': 20}
    product = client.post('/products', headers=farmer, json=product_body).json()['id']
    assert client.put('/cart/items', headers=buyer, json={'product_id': product, 'quantity': 1}).status_code == 200
    body = {'product_id': product, 'quantity': 1, 'fulfillment': 'odbior', 'pickup_point_id': point}
    created = client.post('/orders', headers=buyer, json=body)
    assert created.status_code == 201, created.text
    order = created.json()
    oid = order['id']
    if name == 'confirm':
        assert client.post(f'/test/orders/{oid}/ready', headers=farmer).status_code == 200
    with api.db() as con:
        notification = con.execute('SELECT id FROM notifications WHERE user_id=? ORDER BY id LIMIT 1', (bid,)).fetchone()[0]
    cases = {
        'product_create': ('POST', '/products', product_body, farmer, fid),
        'product_update': ('PATCH', f'/products/mine/{product}', {'stock': 50}, farmer, fid),
        'point_create': ('POST', '/pickup-points', point_body, farmer, fid),
        'point_update': ('PUT', f'/pickup-points/{point}', {**point_body, 'active': False}, farmer, fid),
        'profile': ('PUT', '/farmers/me/profile', {'farm_name': 'Nowy profil', 'city': 'Opole'}, farmer, fid),
        'cart_put': ('PUT', '/cart/items', {'product_id': product, 'quantity': 2}, buyer, bid),
        'cart_delete': ('DELETE', f'/cart/items/{product}', None, buyer, bid),
        'cart_clear': ('DELETE', '/cart/items', None, buyer, bid),
        'notification': ('POST', f'/notifications/{notification}/read', None, buyer, bid),
        'order': ('POST', '/orders', body, buyer, bid),
        'checkout': ('POST', '/cart/checkout-test', {'fulfillment': 'odbior', 'pickup_point_id': point}, buyer, bid),
        'ready': ('POST', f'/test/orders/{oid}/ready', None, farmer, fid),
        'confirm': ('POST', f'/orders/{oid}/confirm', {'pin': order['pin_test_only'], 'checked_goods': True}, farmer, fid),
        'cancel': ('POST', f'/orders/{oid}/cancel-test', None, buyer, bid),
    }
    return client, cases[name]


@pytest.mark.parametrize('name', ['product_create', 'product_update', 'point_create', 'point_update',
                                 'profile', 'cart_put', 'cart_delete', 'cart_clear', 'notification',
                                 'order', 'checkout', 'ready', 'confirm', 'cancel'])
@pytest.mark.parametrize('change', ['revoke', 'expire', 'role'])
def test_write_rechecks_session_after_dependency_snapshot(name, change):
    client, (method, url, body, headers, uid) = scenario(name)
    before = []
    def stale(authorization: str | None = Header(default=None)):
        user = api.current_user(authorization)
        with api.db() as con:
            if change == 'revoke':
                con.execute('DELETE FROM sessions WHERE user_id=?', (uid,))
            elif change == 'expire':
                con.execute('UPDATE sessions SET expires_at=? WHERE user_id=?',
                            ((datetime.now(timezone.utc)-timedelta(seconds=1)).isoformat(), uid))
            else:
                con.execute('UPDATE users SET role=? WHERE id=?',
                            ('klient' if user['role'] == 'rolnik' else 'rolnik', uid))
        before.append(database_digest())
        return user
    api.app.dependency_overrides[api.current_user] = stale
    try:
        result = client.request(method, url, headers=headers, json=body)
    finally:
        api.app.dependency_overrides.pop(api.current_user, None)
    assert result.status_code == (403 if change == 'role' else 401)
    assert result.headers['cache-control'] == 'no-store'
    assert database_digest() == before[0]


def test_concurrent_logout_prevents_a_paused_product_write():
    client = TestClient(api.app)
    headers, uid = actor('rolnik')
    paused, resume = Event(), Event()
    def snapshot(request: Request, authorization: str | None = Header(default=None)):
        user = api.current_user(authorization)
        if request.url.path == '/products' and request.method == 'POST':
            paused.set()
            assert resume.wait(timeout=5), 'Timed out waiting for synthetic logout'
        return user
    api.app.dependency_overrides[api.current_user] = snapshot
    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(client.post, '/products', headers=headers, json={
                'name': 'Zablokowany zapis', 'price_grosze': 199, 'delivery_grosze': 501, 'stock': 1})
            try:
                assert paused.wait(timeout=5)
                assert client.post('/auth/logout', headers=headers).status_code == 200
            finally:
                resume.set()
            assert future.result(timeout=5).status_code == 401
    finally:
        api.app.dependency_overrides.pop(api.current_user, None)
    with api.db() as con:
        assert con.execute('SELECT COUNT(*) FROM products WHERE farmer_id=?', (uid,)).fetchone()[0] == 0


def test_sqlite_write_context_locks_before_refreshing_identity(monkeypatch):
    headers, _ = actor('rolnik')
    user = api.current_user(headers['Authorization'])
    original = api.db
    queries = []
    @contextmanager
    def traced():
        with original() as con:
            con.set_trace_callback(queries.append)
            yield con
    monkeypatch.setattr(api, 'db', traced)
    with api.order_write_db(user, headers['Authorization'], ('rolnik',)) as con:
        assert con.in_transaction
        con.execute('SELECT 1')
    assert queries[0] == 'BEGIN IMMEDIATE'
    assert queries[1].startswith('SELECT u.id,u.role,s.expires_at')
    assert queries[-1] == 'COMMIT'


def test_authenticated_mutations_do_not_open_unverified_connections():
    import ast
    from pathlib import Path
    tree = ast.parse((Path(api.__file__)).read_text(encoding='utf-8'))
    # Reset is intentionally anonymous; confirmation authenticates a single-use token.
    exceptions = {'register', 'login', 'cart_quote', 'search_nearby',
                  'request_test_password_reset', 'confirm_test_password_reset',
                  'request_queued_password_reset', 'confirm_queued_password_reset'}
    unverified = []
    for node in tree.body:
        if not isinstance(node, ast.FunctionDef) or node.name in exceptions:
            continue
        mutation = any(isinstance(d, ast.Call) and isinstance(d.func, ast.Attribute)
                       and d.func.attr in ('post', 'put', 'patch', 'delete')
                       for d in node.decorator_list)
        if mutation and any(isinstance(call, ast.Call) and isinstance(call.func, ast.Name)
                            and call.func.id == 'db' for call in ast.walk(node)):
            unverified.append(node.name)
    assert unverified == []


@pytest.mark.parametrize('change', ['revoke', 'expire', 'role'])
def test_courier_address_read_rechecks_session_in_its_snapshot(change):
    client = TestClient(api.app)
    farmer, _ = actor('rolnik')
    buyer, _ = actor('klient')
    courier, cid = actor('dostawca')
    product = client.post('/products', headers=farmer, json={
        'name': 'Dostawa testowa', 'price_grosze': 199, 'delivery_grosze': 501, 'stock': 2}).json()['id']
    order = client.post('/orders', headers=buyer, json={
        'product_id': product, 'quantity': 1, 'fulfillment': 'dostawa',
        'delivery_city': 'Opole', 'delivery_street': 'Poufna Testowa 91', 'delivery_postal_code': '45-001'}).json()
    oid = order['id']
    assert client.post(f'/orders/{oid}/assign-courier-test', headers=farmer, json={'courier_id': cid}).status_code == 200
    assert client.post(f'/orders/{oid}/dispatch-test', headers=farmer).status_code == 200
    assert any(row['order_id'] == oid for row in client.get('/couriers/me/active-addresses', headers=courier).json())
    def stale(authorization: str | None = Header(default=None)):
        user = api.current_user(authorization)
        with api.db() as con:
            if change == 'revoke':con.execute('DELETE FROM sessions WHERE user_id=?', (cid,))
            elif change == 'expire':con.execute('UPDATE sessions SET expires_at=? WHERE user_id=?', ('2000-01-01T00:00:00+00:00',cid))
            else:con.execute('UPDATE users SET role=? WHERE id=?', ('klient',cid))
        return user
    api.app.dependency_overrides[api.current_user] = stale
    try:response = client.get('/couriers/me/active-addresses', headers=courier)
    finally:api.app.dependency_overrides.pop(api.current_user, None)
    assert response.status_code == (403 if change == 'role' else 401)
    assert 'Poufna Testowa 91' not in response.text
    assert response.headers['cache-control'] == 'no-store'

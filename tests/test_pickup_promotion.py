"""Campaign expiry, seller isolation, retry safety and real API point coverage."""
from datetime import datetime
from uuid import uuid4
from zoneinfo import ZoneInfo
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient
from backend import app as module, pickup_promotion as promotion

URL = '/farmers/me/pickup-promotion'


@pytest.fixture
def promotion_api(monkeypatch):
    monkeypatch.setenv('WP_ENABLE_PICKUP_PROMOTION', '1')
    monkeypatch.setattr(promotion, 'now_epoch', lambda: promotion.EXPIRES_AT-40*86400)
    with module.db() as con:
        con.executescript(promotion.SCHEMA_SQLITE)
    client = TestClient(module.app)
    people = []
    for role in ('rolnik', 'rolnik', 'klient'):
        body = {'email': uuid4().hex+'@example.invalid', 'password': 'PromoTestPassword2026!', 'role': role}
        result = client.post('/auth/register', json=body)
        assert result.status_code == 201
        token = client.post('/auth/login', json=body).json()['access_token']
        people.append(({'Authorization': 'Bearer '+token}, result.json()['id']))
    yield client, people


def point(client, headers, name='Punkt promocji'):
    result = client.post('/pickup-points', headers=headers, json={
        'name': name, 'city': 'Legnica', 'street': 'Testowa 12', 'opening_hours': '7–10'})
    assert result.status_code == 201
    return result.json()['id']


@pytest.mark.parametrize('code', ['WIEJSKAPAKA', 'wiejska paka', ' WiejskaPaka '])
def test_code_redeems_once_without_extending_calendar_expiry(promotion_api, monkeypatch, code):
    client, users = promotion_api
    headers, seller = users[0]
    assert not client.get(URL, headers=headers).json()['redeemed']
    first = client.post(URL, headers=headers, json={'code': code})
    assert first.status_code == 200
    data = first.json()
    assert data['active'] and data['remaining'] == 3 and data['point_limit'] == 3
    assert data['ends_at'] == '2027-01-01T00:00:00+01:00'
    with module.db() as con:
        original = dict(con.execute('SELECT * FROM pickup_promotion_grants WHERE farmer_id=?', (seller,)).fetchone())
    monkeypatch.setattr(promotion, 'now_epoch', lambda: promotion.EXPIRES_AT-1)
    assert client.post(URL, headers=headers, json={'code': code}).status_code == 200
    with module.db() as con:
        rows = con.execute('SELECT * FROM pickup_promotion_grants WHERE farmer_id=?', (seller,)).fetchall()
        assert len(rows) == 1 and dict(rows[0]) == original
    assert not client.get(URL, headers=users[1][0]).json()['redeemed']


def test_only_three_active_seller_places_are_covered_and_new_places_use_remaining_slots(promotion_api):
    client, users = promotion_api
    headers = users[0][0]
    foreign = point(client, users[1][0])
    assert client.post(URL, headers=headers, json={'code': promotion.CODE}).status_code == 200
    ids = []
    for _ in range(4):
        ids.append(point(client, headers))
        data = client.get(URL, headers=headers).json()
        assert data['covered_point_ids'] == ids[:3]
        assert data['remaining'] == max(0, 3-len(ids))
    assert foreign not in data['covered_point_ids']
    with module.db() as con:
        con.execute('UPDATE pickup_points SET active=0 WHERE id=?', (ids[0],))
    assert client.get(URL, headers=headers).json()['covered_point_ids'] == ids[1:]
    with module.db() as con:
        con.execute('UPDATE pickup_points SET active=1 WHERE id=?', (ids[0],))
    assert client.get(URL, headers=headers).json()['covered_point_ids'] == ids[:3]


def test_expiry_is_midnight_in_poland_and_does_not_disable_points(promotion_api, monkeypatch):
    client, users = promotion_api
    headers = users[0][0]
    pid = point(client, headers)
    assert client.post(URL, headers=headers, json={'code': promotion.CODE}).status_code == 200
    assert datetime.fromtimestamp(promotion.EXPIRES_AT, ZoneInfo('Europe/Warsaw')).isoformat() == promotion.ENDS_AT
    monkeypatch.setattr(promotion, 'now_epoch', lambda: promotion.EXPIRES_AT-1)
    assert client.get(URL, headers=headers).json()['covered_point_ids'] == [pid]
    monkeypatch.setattr(promotion, 'now_epoch', lambda: promotion.EXPIRES_AT)
    data = client.get(URL, headers=headers).json()
    assert data['expired'] and data['redeemed'] and not data['active']
    assert data['covered_point_ids'] == [] and data['remaining'] == 0
    assert client.post(URL, headers=headers, json={'code': promotion.CODE}).status_code == 410
    assert client.post(URL, headers=users[1][0], json={'code': promotion.CODE}).status_code == 410
    assert next(p for p in client.get('/farmers/me/pickup-points', headers=headers).json() if p['id'] == pid)['active'] == 1


def test_invalid_inputs_and_roles_cannot_grant_or_change_others_entitlement(promotion_api, monkeypatch):
    client, users = promotion_api
    assert client.get(URL).status_code == 401
    assert client.post(URL, json={'code': promotion.CODE}).status_code == 401
    for method in ('GET', 'POST'):
        response = client.request(method, URL, headers=users[2][0], **({'json': {'code': promotion.CODE}} if method == 'POST' else {}))
        assert response.status_code == 403
    for body in ({'code': 'BAD'}, {'code': 123}, {'code': 'x'*41},
                 {'code': promotion.CODE, 'farmer_id': users[1][1]},
                 {'code': promotion.CODE, 'expires_at': promotion.EXPIRES_AT+86400},
                 {'code': promotion.CODE, 'point_limit': 99}):
        assert client.post(URL, headers=users[0][0], json=body).status_code == 422
    monkeypatch.setenv('WP_ENABLE_PICKUP_PROMOTION', '0')
    assert client.get(URL, headers=users[0][0]).json() == {'enabled': False}
    assert client.post(URL, headers=users[0][0], json={'code': promotion.CODE}).status_code == 503


def test_revoked_session_is_rechecked_inside_transaction(promotion_api):
    client, users = promotion_api
    headers, seller = users[0]
    old_user = client.get('/auth/me', headers=headers).json()
    with module.db() as con:
        con.execute('DELETE FROM sessions WHERE user_id=?', (seller,))
    module.app.dependency_overrides[module.current_user] = lambda: old_user
    try:
        assert client.get(URL, headers=headers).status_code == 401
        assert client.post(URL, headers=headers, json={'code': promotion.CODE}).status_code == 401
        with module.db() as con:
            assert con.execute('SELECT count(*) AS n FROM pickup_promotion_grants WHERE farmer_id=?', (seller,)).fetchone()['n'] == 0
    finally:
        module.app.dependency_overrides.pop(module.current_user, None)


def test_concurrent_redemptions_keep_one_grant(promotion_api):
    client, users = promotion_api
    def redeem(_):
        return client.post(URL, headers=users[0][0], json={'code': promotion.CODE}).status_code
    with ThreadPoolExecutor(max_workers=3) as pool:
        assert list(pool.map(redeem, range(6))) == [200]*6
    with module.db() as con:
        assert con.execute('SELECT count(*) AS n FROM pickup_promotion_grants WHERE farmer_id=?', (users[0][1],)).fetchone()['n'] == 1

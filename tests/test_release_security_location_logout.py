"""Regression: PostgreSQL location reads and global logout must reverify sessions."""
from contextlib import contextmanager
from fastapi import HTTPException
import pytest
from backend import app as api


@pytest.fixture
def guarded(monkeypatch):
    class Calls(list):pass
    calls=Calls();calls.connection=FakeConnection()
    @contextmanager
    def fake_guard(user, authorization, roles):
        calls.append((user['id'], authorization, tuple(roles)))
        if authorization != 'Bearer valid':
            raise HTTPException(401, 'Sesja nieważna')
        yield calls.connection
    monkeypatch.setattr(api, 'order_write_db', fake_guard)
    return calls


class FakeConnection:
    def __init__(self):self.queries=[]
    def execute(self, sql, params=()):
        self.queries.append(sql)
        if sql.startswith('SELECT u.id,u.role,s.expires_at'):
            return FakeResult({'id':10,'role':'klient','expires_at':'2100-01-01T00:00:00Z'})
        if sql.startswith('SELECT o.buyer_id'):
            return FakeResult({'buyer_id': 10, 'farmer_id': 20,
                'fulfillment': 'dostawa', 'status': 'w_drodze_testowo',
                'pin_used': 0, 'confirmed_at': None, 'pickup_point_id': None,
                'delivery_city': 'Kraków', 'delivery_street': 'Testowa 1',
                'delivery_postal_code': '30-001', 'courier_id': 30})
        return FakeResult(None)


class FakeResult:
    def __init__(self, row):
        self.row = row
    def fetchone(self):
        return self.row


def test_location_uses_verified_transaction(guarded):
    result = api.order_location(123, {'id': 10, 'role': 'klient'}, 'Bearer valid')
    assert result['delivery_city'] == 'Kraków'
    assert guarded == [(10, 'Bearer valid', ('klient', 'rolnik', 'dostawca'))]


def test_location_rejects_unverified_session(guarded):
    with pytest.raises(HTTPException) as err:
        api.order_location(123, {'id': 10, 'role': 'klient'}, 'Bearer invalid')
    assert err.value.status_code == 401


def test_logout_all_uses_verified_transaction(guarded):
    assert api.logout_all({'id': 10, 'role': 'klient'}, 'Bearer valid')['ok']
    assert guarded == [(10, 'Bearer valid', ('klient', 'rolnik', 'dostawca', 'admin'))]
    queries=guarded.connection.queries
    # The mocked order_write_db owns BEGIN; the account helper still refreshes
    # the actor after the PostgreSQL account lock before deleting any session.
    assert queries[0].startswith('SELECT u.id,u.role,s.expires_at')
    assert queries[1]=='DELETE FROM sessions WHERE user_id=?'


def test_logout_all_rejects_unverified_session(guarded):
    with pytest.raises(HTTPException) as err:
        api.logout_all({'id': 10, 'role': 'klient'}, 'Bearer invalid')
    assert err.value.status_code == 401

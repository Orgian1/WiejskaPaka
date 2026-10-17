"""Endpoint contract tests; no external Neon credentials required."""
from contextlib import contextmanager
from unittest.mock import patch
import pytest
from fastapi import HTTPException
from backend import app as api

class FakeConn:
    def __init__(self):
        self.calls = []
    def execute(self, sql, params=()):
        self.calls.append((sql, params))
        return self
    def fetchall(self):
        return [{'order_id': 7, 'delivery_city': 'Testowo',
                 'delivery_street': 'Testowa 1', 'delivery_postal_code': '00-001'}]
    def fetchone(self):
        return {'id':91,'role':'dostawca','expires_at':'2100-01-01T00:00:00+00:00'}

@contextmanager
def fake_db(conn):
    yield conn

def test_courier_active_addresses_uses_verified_identity_and_filters():
    con = FakeConn()
    with patch.object(api, 'db', lambda: fake_db(con)):
        result = api.courier_active_addresses({'id': 91, 'role': 'dostawca'}, 'Bearer synthetic-token')
    assert result[0]['order_id'] == 7
    assert con.calls[0][0] == 'BEGIN'
    assert con.calls[1][0].startswith('SELECT u.id,u.role,s.expires_at')
    sql, params = con.calls[2]
    assert params == (91,)
    for fragment in ('a.courier_id=?', "o.fulfillment='dostawa'",
                     "o.status='w_drodze_testowo'", 'o.pin_used=0',
                     'o.confirmed_at IS NULL'):
        assert fragment in sql
    assert 'phone' not in sql.lower() and 'email' not in sql.lower()

def test_other_roles_denied_before_database_read():
    for role in ('klient', 'rolnik', 'admin'):
        with pytest.raises(HTTPException) as err:
            api.courier_active_addresses({'id': 91, 'role': role})
        assert err.value.status_code == 403

def test_route_requires_session_dependency():
    route = next(r for r in api.app.routes if getattr(r, 'path', '') == '/couriers/me/active-addresses')
    assert 'GET' in route.methods
    assert any(d.call is api.current_user for d in route.dependant.dependencies)

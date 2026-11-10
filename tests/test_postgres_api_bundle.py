"""PostgreSQL /orders/me must re-authenticate inside its read transaction."""
from contextlib import contextmanager
from unittest.mock import patch
import pytest
from fastapi import HTTPException
from backend import app as api


class FakeCon:
    def __init__(self, role):
        self.role = role
        self.sql = []

    def execute(self, sql, params=()):
        self.sql.append((sql, params))
        return self

    def fetchone(self):
        return {'role': self.role} if self.role else None

    def fetchall(self):
        return [{'id': 11, 'status': 'w_drodze_testowo'}]


@pytest.mark.parametrize('role,scope', [('klient', 'buyer_id'), ('rolnik', 'farmer_id')])
def test_postgres_order_list_scoped_to_verified_actor(role, scope):
    con = FakeCon(role)
    @contextmanager
    def verified(url, header):
        assert header == 'Bearer verified'
        yield con, 42
    with patch.object(api, 'DATABASE_URL', 'postgresql://fake'), patch('backend.pg_adapter.postgres_verified_db', verified):
        result = api.my_orders(user={'id': 999, 'role': 'admin'}, authorization='Bearer verified')
    assert result == [{'id': 11, 'status': 'w_drodze_testowo'}]
    assert any(scope in sql and params == (42,) for sql, params in con.sql)
    assert all(999 not in params for _, params in con.sql)


def test_postgres_order_list_rejects_other_role():
    con = FakeCon('dostawca')
    @contextmanager
    def verified(url, header):
        yield con, 42
    with patch.object(api, 'DATABASE_URL', 'postgresql://fake'), patch('backend.pg_adapter.postgres_verified_db', verified):
        with pytest.raises(HTTPException) as exc:
            api.my_orders(user={'id': 42}, authorization='Bearer verified')
    assert exc.value.status_code == 403
    assert not any('FROM orders' in sql for sql, _ in con.sql)


def test_postgres_order_list_rejects_invalid_session():
    from backend.neon_session_bridge import AuthenticationFailed
    @contextmanager
    def verified(url, header):
        raise AuthenticationFailed('invalid')
        yield
    with patch.object(api, 'DATABASE_URL', 'postgresql://fake'), patch('backend.pg_adapter.postgres_verified_db', verified):
        with pytest.raises(HTTPException) as exc:
            api.my_orders(user={'id': 42}, authorization='Bearer invalid')
    assert exc.value.status_code == 401


def test_postgres_courier_address_list_scoped_to_verified_actor():
    con = FakeCon('dostawca')
    @contextmanager
    def verified(url, header):
        yield con, 73
    with patch.object(api, 'DATABASE_URL', 'postgresql://fake'), patch('backend.pg_adapter.postgres_verified_db', verified):
        api.courier_active_addresses(user={'id': 999, 'role': 'dostawca'}, authorization='Bearer verified')
    sql, params = next((sql, params) for sql, params in con.sql if 'JOIN delivery_assignments' in sql)
    assert params == (73, 'w_drodze_testowo')
    assert 'o.pin_used = 0' in sql and 'o.confirmed_at IS NULL' in sql
    assert 'phone' not in sql.lower()


def test_postgres_courier_address_list_rejects_role_change():
    con = FakeCon('klient')
    @contextmanager
    def verified(url, header):
        yield con, 73
    with patch.object(api, 'DATABASE_URL', 'postgresql://fake'), patch('backend.pg_adapter.postgres_verified_db', verified):
        with pytest.raises(HTTPException) as exc:
            api.courier_active_addresses(user={'id': 73, 'role': 'dostawca'}, authorization='Bearer verified')
    assert exc.value.status_code == 403

from contextlib import contextmanager
from unittest.mock import patch
import pytest
from backend.verified_writes import verified_order_write, WriteAuthorizationError

@contextmanager
def fake_db(actor):
    yield object(), actor

@pytest.mark.parametrize('actor,expected_role,actual_role,should_allow', [
    (7,'rolnik','rolnik',True),
    (8,'rolnik','rolnik',False),
    (7,'rolnik',None,False),
    (7,'rolnik','klient',False),
])
def test_verified_write_checks_actor_and_role(actor, expected_role, actual_role, should_allow):
    with patch('backend.pg_adapter.postgres_verified_db', side_effect=lambda *a, **k: fake_db(actor)), \
         patch('backend.neon_auth_policy.actor_role', return_value=actual_role) as role_lookup:
        if should_allow:
            with verified_order_write('test-url','Bearer abc',{'id':7,'role':expected_role},('rolnik',)):
                pass
            role_lookup.assert_called_once()
        else:
            with pytest.raises(WriteAuthorizationError):
                with verified_order_write('test-url','Bearer abc',{'id':7,'role':expected_role},('rolnik',)):
                    pass

def test_verified_write_propagates_database_error():
    with patch('backend.pg_adapter.postgres_verified_db', side_effect=RuntimeError('db down')):
        with pytest.raises(RuntimeError, match='db down'):
            with verified_order_write('test-url','Bearer abc',{'id':7,'role':'rolnik'},('rolnik',)):
                pass

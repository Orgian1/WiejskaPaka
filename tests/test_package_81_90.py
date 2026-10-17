"""Regression checks for previously unverified API routes."""
from contextlib import contextmanager
from unittest.mock import patch, MagicMock
from backend import app as module

@contextmanager
def fake_verified(user, authorization, roles):
    assert authorization == 'Bearer test-token'
    assert user['role'] in roles
    con = MagicMock()
    con.execute.return_value.__iter__.return_value = iter([{'id': 3, 'name': 'Jablka'}])
    yield con

def test_farmer_products_use_verified_context():
    farmer = {'id': 9, 'role': 'rolnik'}
    with patch.object(module, 'order_write_db', side_effect=fake_verified) as verified:
        assert module.my_products(user=farmer, authorization='Bearer test-token')[0]['id'] == 3
        verified.assert_called_once()
        assert verified.call_args.args[2] == ('rolnik',)

def test_cancel_uses_verified_context_before_any_write():
    buyer = {'id': 9, 'role': 'klient'}
    with patch.object(module, 'order_write_db', side_effect=fake_verified) as verified:
        try:
            module.cancel_order_test(12, user=buyer, authorization='Bearer test-token')
        except Exception:
            pass  # fake cursor does not model a complete order
        verified.assert_called_once()
        assert verified.call_args.args[2] == ('klient',)

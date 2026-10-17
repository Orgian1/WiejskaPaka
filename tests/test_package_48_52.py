"""Regression tests for transaction-bound test-payment events."""
from contextlib import contextmanager
from unittest.mock import Mock
import pytest
from fastapi import HTTPException
from backend import app as api


def test_payment_event_endpoint_declares_bearer_header():
    import inspect
    signature = inspect.signature(api.post_payment_test)
    assert 'authorization' in signature.parameters


def test_payment_event_uses_verified_write_transaction(monkeypatch):
    monkeypatch.setenv('WP_ENABLE_TEST_PAYMENTS', '1')
    calls = []
    @contextmanager
    def fake_verified(user, authorization, roles):
        calls.append((user['id'], authorization, roles))
        raise HTTPException(401, 'Sesja nieważna')
        yield  # pragma: no cover
    monkeypatch.setattr(api, 'order_write_db', fake_verified)
    with pytest.raises(HTTPException) as error:
        api.post_payment_test(1, api.TestPaymentEventIn(event_id='verify-boundary', event_type='payment_success_test'),
                              {'id': 7, 'role': 'klient'}, 'Bearer invalid')
    assert error.value.status_code == 401
    assert calls == [(7, 'Bearer invalid', ('klient', 'rolnik'))]


def test_payment_events_remain_disabled_without_flag(monkeypatch):
    monkeypatch.delenv('WP_ENABLE_TEST_PAYMENTS', raising=False)
    with pytest.raises(HTTPException) as error:
        api.post_payment_test(1, Mock(), {'id': 7, 'role': 'klient'}, None)
    assert error.value.status_code == 404

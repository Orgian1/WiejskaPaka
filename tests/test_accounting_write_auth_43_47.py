"""Regression checks: PostgreSQL accounting writes require transaction-bound auth."""
import inspect
import pytest
from fastapi import HTTPException
from backend import app as module

@pytest.mark.parametrize('endpoint', [
    module.create_commission_draft,
    module.create_invoice_draft,
    module.request_invoice_correction,
    module.prepare_accounting_export,
    module.validate_accounting_export,
    module.acknowledge_accounting_validation,
    module.reconcile_test_finance,
])
def test_accounting_write_endpoints_accept_authorization(endpoint):
    assert 'authorization' in inspect.signature(endpoint).parameters

@pytest.mark.parametrize('role', ['rolnik', 'admin'])
def test_order_write_db_denies_mismatched_pg_actor(monkeypatch, role):
    import backend.verified_writes as writes
    from contextlib import contextmanager
    @contextmanager
    def fake_verified(*args, **kwargs):
        raise writes.WriteAuthorizationError('Mismatch')
        yield
    monkeypatch.setattr(writes, 'verified_order_write', fake_verified)
    monkeypatch.setattr(module, 'DATABASE_URL', 'postgresql://test.invalid/db')
    with pytest.raises(HTTPException) as exc:
        with module.order_write_db({'id': 1, 'role': role}, 'Bearer invalid', (role,)):
            pass
    assert exc.value.status_code == 403

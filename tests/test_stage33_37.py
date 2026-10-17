"""Regression checks: PostgreSQL write routes must use transaction-bound actor verification."""
import inspect
from backend import app


def test_product_create_requires_verified_write():
    source = inspect.getsource(app.create_product)
    assert "order_write_db(user, authorization, ('rolnik',))" in source
    assert 'user[\'id\']' in source


def test_logout_requires_verified_write():
    source = inspect.getsource(app.logout)
    assert 'account_session_db(user,authorization)' in source
    guard=inspect.getsource(app.account_session_db)
    assert 'order_write_db(user,authorization,roles)' in guard
    assert guard.index('BEGIN IMMEDIATE')<guard.index('authorize_transaction(')
    assert guard.index('pg_advisory_xact_lock')<guard.index('authorize_transaction(')
    assert 'token_hash(authorization[7:])' in source


def test_farmer_acknowledgement_requires_verified_write():
    source = inspect.getsource(app.acknowledge_compliance)
    assert "order_write_db(user, authorization, ('rolnik',))" in source


def test_admin_review_requires_verified_write():
    source = inspect.getsource(app.review_farmer_compliance)
    assert "order_write_db(user, authorization, ('admin',))" in source


def test_verified_write_rechecks_role_and_identity():
    from backend import verified_writes
    source = inspect.getsource(verified_writes.verified_order_write)
    assert "actor_id != expected_user['id']" in source
    assert "role != expected_user['role']" in source

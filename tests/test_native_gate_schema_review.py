"""Offline verification of native gate provisioning; no PostgreSQL claims."""
import hashlib
from pathlib import Path

import pytest

from tests.test_postgres_full_api_optin import reviewed_test_schema


def test_native_gate_uses_reviewed_manifest_order(monkeypatch, tmp_path):
    import database.verify_test_migrations as verifier
    names = ('base.sql', 'z_first.sql', 'a_second.sql')
    entries = []
    for name in names:
        content = ('-- Zażółć ' + name + '\n').encode('utf-8')
        (tmp_path / name).write_bytes(content)
        entries.append({'file': name, 'sha256': hashlib.sha256(content).hexdigest()})
    monkeypatch.setattr(verifier, 'verify', lambda root: {'ok': True, 'files': entries})
    assert reviewed_test_schema(tmp_path) == tuple('-- Zażółć ' + name + '\n' for name in names)


def test_native_gate_rejects_review_failure(monkeypatch, tmp_path):
    import database.verify_test_migrations as verifier
    monkeypatch.setattr(verifier, 'verify', lambda root: {'ok': False, 'files': []})
    with pytest.raises(ValueError, match='review failed'):
        reviewed_test_schema(tmp_path)


def test_native_gate_rejects_sql_changed_after_verification(monkeypatch, tmp_path):
    import database.verify_test_migrations as verifier
    (tmp_path / 'base.sql').write_bytes(b'changed')
    monkeypatch.setattr(verifier, 'verify', lambda root: {'ok': True, 'files': [
        {'file': 'base.sql', 'sha256': hashlib.sha256(b'reviewed').hexdigest()}]})
    with pytest.raises(ValueError, match='changed during review'):
        reviewed_test_schema(tmp_path)


def test_native_gate_reviews_before_any_database_connection(monkeypatch):
    import psycopg
    import tests.test_postgres_full_api_optin as gate
    monkeypatch.setenv('WP_TEST_POSTGRES_DSN', 'postgresql://test:test@127.0.0.1/wp_test_probe')
    def rejected(root):
        raise ValueError('synthetic migration rejection')
    monkeypatch.setattr(gate, 'reviewed_test_schema', rejected)
    monkeypatch.setattr(psycopg, 'connect', lambda *a, **k: pytest.fail('Unexpected connection'))
    probe = gate.pg_api.__wrapped__()
    with pytest.raises(ValueError, match='synthetic migration rejection'):
        next(probe)


def test_repository_schema_snapshot_is_current():
    root = Path(__file__).resolve().parents[1] / 'database'
    from database.test_schema_manifest import BASE, UPGRADES
    assert reviewed_test_schema(root) == tuple(
        (root / name).read_text(encoding='utf-8') for name in (BASE, *UPGRADES))

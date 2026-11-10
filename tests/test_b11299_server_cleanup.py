"""B/11299: server startup never leaks the temporary database credential."""
import os
import sys
import types
from unittest.mock import patch
import pytest
from backend import test_server_launcher as launcher

DSN = 'postgresql://localhost/wp_test'

@pytest.fixture
def isolated(monkeypatch):
    for key in ('DATABASE_URL', 'WP_TEST_DATABASE_URL', 'WP_ENV', 'WP_BIND_HOST', 'WIEJSKAPAKA_DB'):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv('WP_TEST_DATABASE_URL', DSN)
    monkeypatch.setenv('WP_ENV', 'test')
    monkeypatch.setenv('WP_BIND_HOST', '127.0.0.1')

@pytest.mark.parametrize('fail', [False, True])
def test_temporary_dsn_removed_after_uvicorn_returns_or_fails(isolated, fail):
    def run(*args, **kwargs):
        assert os.environ['DATABASE_URL'] == DSN
        if fail:
            raise RuntimeError('server failed')
    with patch.object(launcher, 'verify_test_database_connection'), patch.dict(sys.modules, {'uvicorn': types.SimpleNamespace(run=run)}):
        if fail:
            with pytest.raises(RuntimeError, match='server failed'):
                launcher.main()
        else:
            launcher.main()
    assert 'DATABASE_URL' not in os.environ

def test_existing_matching_dsn_restored_after_shutdown(isolated, monkeypatch):
    monkeypatch.setenv('DATABASE_URL', DSN)
    with patch.object(launcher, 'verify_test_database_connection'), patch.dict(sys.modules, {'uvicorn': types.SimpleNamespace(run=lambda *a, **k: None)}):
        launcher.main()
    assert os.environ['DATABASE_URL'] == DSN

def test_preflight_failure_does_not_mutate_database_url(isolated, monkeypatch):
    monkeypatch.setenv('WP_BIND_HOST', '0.0.0.0')
    with pytest.raises(ValueError):
        launcher.main()
    assert 'DATABASE_URL' not in os.environ

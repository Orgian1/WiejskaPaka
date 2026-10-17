"""The unverified database URL must never be exported to the API process."""
import os
import sys
import types
from unittest.mock import patch
import pytest
from backend import test_server_launcher as launcher


def env():
    return {'WP_ENV':'test', 'WP_TEST_DATABASE_URL':'postgresql://localhost/wp_test', 'WP_BIND_HOST':'127.0.0.1'}


def test_failed_database_probe_does_not_export_database_url(monkeypatch):
    for key in ('DATABASE_URL','WP_TEST_DATABASE_URL','WP_ENV','WP_BIND_HOST','WIEJSKAPAKA_DB'):
        monkeypatch.delenv(key, raising=False)
    for key,value in env().items(): monkeypatch.setenv(key,value)
    def fail(*args,**kwargs):
        assert 'DATABASE_URL' not in os.environ
        raise RuntimeError('schema incomplete')
    with patch.object(launcher, 'verify_test_database_connection', side_effect=fail):
        with pytest.raises(RuntimeError,match='preflight failed'):
            launcher.main()
    assert 'DATABASE_URL' not in os.environ


def test_successful_probe_exports_only_after_validation(monkeypatch):
    for key in ('DATABASE_URL','WP_TEST_DATABASE_URL','WP_ENV','WP_BIND_HOST','WIEJSKAPAKA_DB'):
        monkeypatch.delenv(key, raising=False)
    for key,value in env().items(): monkeypatch.setenv(key,value)
    calls=[]
    def verify(dsn,name,*,require_schema):
        assert 'DATABASE_URL' not in os.environ
        assert name=='wp_test' and require_schema
        calls.append('verified')
    fake_uvicorn=types.SimpleNamespace(run=lambda *a,**kw: calls.append(('run',os.environ['DATABASE_URL'],kw['workers'])))
    with patch.object(launcher,'verify_test_database_connection',side_effect=verify), patch.dict(sys.modules,{'uvicorn':fake_uvicorn}):
        launcher.main()
    assert calls==['verified',('run',env()['WP_TEST_DATABASE_URL'],1)]

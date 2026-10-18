"""Private preview probe: no API import, secrets in reports or remote connection."""
import json
import os
from pathlib import Path
from unittest.mock import Mock
import pytest
from backend.checkout_vault import create_ring
from scripts.check_postgres_preview import inspect_preview
from backend.postgres_schema_preflight import CORE_TABLES


def configuration(tmp_path):
    key = tmp_path/'private.checkout-key';create_ring(key)
    return {'WP_ENV': 'test', 'WP_TEST_DATABASE_URL':
        'postgresql://app:private-password@127.0.0.1/wp_test_preview',
        'WP_CHECKOUT_KEY_FILE': str(key)}


class Connection:
    def __init__(self, *, privileged=False, missing=False, wrong=False):
        self.values = [('other' if wrong else 'wp_test_preview',),
                       (privileged, False, False, False)]
        self.missing = missing
        self.queries = []
        self.closed = False
    def cursor(self):return self
    def __enter__(self):return self
    def __exit__(self, *args):pass
    def execute(self, query, *args):
        assert query.startswith('SELECT ')
        self.queries.append(query)
    def fetchone(self):return self.values.pop(0)
    def fetchall(self):return [] if self.missing else [(x,) for x in CORE_TABLES]
    def close(self):self.closed = True


def test_success_is_readonly_and_does_not_claim_deployment(tmp_path):
    con = Connection();connect = Mock(return_value=con)
    report = inspect_preview(configuration(tmp_path), connect=connect)
    assert report['success'] and report['database_core_checked'] and con.closed
    assert not report['ready_for_production'] and not report['preview_started']
    assert not report['backup_restore_verified']
    options = connect.call_args.kwargs['options']
    assert 'default_transaction_read_only=on' in options
    assert 'statement_timeout=5000' in options
    text = json.dumps(report)
    assert 'private-password' not in text and str(tmp_path) not in text


@pytest.mark.parametrize('problem', ['privileged', 'missing', 'wrong'])
def test_database_failure_closes_connection_and_is_sanitized(tmp_path, problem):
    con = Connection(**{problem: True})
    report = inspect_preview(configuration(tmp_path), connect=Mock(return_value=con))
    assert not report['success'] and report['error'] == 'DATABASE_PROBE_FAILED'
    assert con.closed


@pytest.mark.parametrize('change', [
    {'WP_ENV': 'production'},
    {'WP_TEST_DATABASE_URL': 'postgresql://app:secret@remote.example/wp_test_preview?sslmode=verify-full'},
    {'DATABASE_URL': 'postgresql://foreign/production'},
    {'WP_AUTO_INIT_POSTGRES': '0'},
    {'WP_REAL_PAYMENTS': '1'},
])
def test_unsafe_configuration_never_connects(tmp_path, change):
    env = configuration(tmp_path);env.update(change);connect = Mock()
    report = inspect_preview(env, connect=connect)
    assert report['error'] == 'CONFIGURATION_REJECTED'
    connect.assert_not_called()


@pytest.mark.parametrize('problem', ['missing', 'invalid', 'relative', 'symlink'])
def test_invalid_key_never_connects_or_gets_created(tmp_path, problem):
    if problem == 'symlink' and os.name != 'posix':
        pytest.skip('Symlink privilege is not guaranteed on Windows')
    env = configuration(tmp_path);key = Path(env['WP_CHECKOUT_KEY_FILE'])
    if problem == 'missing':key.unlink()
    elif problem == 'invalid':key.write_text('private-invalid-contents')
    elif problem == 'relative':env['WP_CHECKOUT_KEY_FILE'] = 'relative.checkout-key'
    else:
        link = tmp_path/'link';link.symlink_to(key);env['WP_CHECKOUT_KEY_FILE'] = str(link)
    connect = Mock();report = inspect_preview(env, connect=connect)
    assert report['error'] == 'CHECKOUT_KEY_REJECTED'
    connect.assert_not_called()
    assert 'private-invalid-contents' not in json.dumps(report)
    if problem == 'missing':assert not key.exists()


def test_driver_exception_never_leaks_secret(tmp_path):
    connect = Mock(side_effect=RuntimeError('private-password /secret/key host.internal'))
    report = inspect_preview(configuration(tmp_path), connect=connect)
    assert report['error'] == 'DATABASE_PROBE_FAILED'
    assert 'private-password' not in json.dumps(report)
    assert '/secret/key' not in json.dumps(report)

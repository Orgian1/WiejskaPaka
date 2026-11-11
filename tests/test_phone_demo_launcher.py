"""Testy izolacji podglądu UI i serwowania strony."""
from pathlib import Path
import os
from unittest.mock import patch
import pytest

from scripts.run_phone_demo import demo_environment, main


def test_geocoder_is_explicit_and_does_not_restore_other_services(monkeypatch):
    monkeypatch.setenv('WP_ENABLE_ADDRESS_SEARCH', '1')
    monkeypatch.setenv('WP_ADDRESS_SEARCH_URL', 'https://inherited.invalid/search')
    monkeypatch.setenv('WP_ENABLE_ORDER_SMTP', '1')
    monkeypatch.setenv('PAYU_CLIENT_SECRET', 'private')
    with patch('scripts.run_phone_demo.subprocess.call', return_value=0) as runner:
        assert main([]) == 0
        assert 'WP_ADDRESS_SEARCH_URL' not in runner.call_args.kwargs['env']
        assert main(['--address-search-url', 'https://chosen.invalid/search']) == 0
        env = runner.call_args.kwargs['env']
        assert env['WP_ADDRESS_SEARCH_URL'] == 'https://chosen.invalid/search'
        assert env['WP_ENABLE_ADDRESS_SEARCH'] == '1'
        assert 'WP_ENABLE_ORDER_SMTP' not in env
        assert 'PAYU_CLIENT_SECRET' not in env
        assert 'DATABASE_URL' not in env
    assert os.environ['WP_ADDRESS_SEARCH_URL'] == 'https://inherited.invalid/search'


@pytest.mark.parametrize('url', ['', 'http://geo.invalid/search',
    'https://user:private@geo.invalid/search', 'https://geo.invalid/search?key=private',
    'https://nominatim.openstreetmap.org/search', 'https://geo.invalid:bad/search',
    'https://geo.invalid:70000/search', 'https://geo.invalid:0/search',
    'https://geo.invalid/\nsearch'])
def test_invalid_geocoder_stops_before_creating_demo(url, capsys):
    with patch('scripts.run_phone_demo.subprocess.call') as runner, \
            patch('scripts.run_phone_demo.subprocess.run') as setup:
        with pytest.raises(SystemExit) as error:
            main(['--full-demo', '--address-search-url', url])
        assert error.value.code == 2
        runner.assert_not_called()
        setup.assert_not_called()
    assert 'private' not in capsys.readouterr().err


def test_demo_environment_drops_external_database_config():
    source = {'DATABASE_URL': 'postgresql://example.invalid/production',
              'WP_TEST_DATABASE_URL': 'postgresql://example.invalid/test',
              'WP_TEST_POSTGRES_DSN': 'secret',
              'WP_ALLOW_REMOTE_DISPOSABLE_TEST_DB': 'YES_I_CONFIRM',
              'WP_ENABLE_TEST_PASSWORD_RESET': '1',
              'WP_TEST_RESET_OUTBOX': '/untrusted/outbox',
              'PATH': '/usr/bin'}
    result = demo_environment(source, Path('/tmp/isolated_demo.sqlite3'))
    assert all(key not in result for key in source if key.startswith(('DATABASE_URL', 'WP_TEST_', 'WP_ALLOW_')))
    assert Path(result['WIEJSKAPAKA_DB']) == Path('/tmp/isolated_demo.sqlite3')
    assert result['PATH'] == '/usr/bin'
    assert 'WP_ENABLE_TEST_PASSWORD_RESET' not in result


def test_demo_launcher_binds_only_to_loopback():
    with patch('scripts.run_phone_demo.subprocess.call', return_value=0) as runner:
        assert main(['--port', '8766']) == 0
    command = runner.call_args.args[0]
    assert command[command.index('--host') + 1] == '127.0.0.1'
    assert command[command.index('--port') + 1] == '8766'
    assert 'DATABASE_URL' not in runner.call_args.kwargs['env']


def test_basic_demo_keeps_local_features_without_inheriting_services(tmp_path):
    source = {'PATH': '/usr/bin', 'WP_ENABLE_PRODUCT_UNITS': '1',
              'WP_ENABLE_ORDER_SMTP': '1', 'WP_ENABLE_SMTP': '1',
              'WP_ENABLE_VERIFICATION_SMTP': '1', 'WP_SMTP_PASSWORD': 'private',
              'AWS_SECRET_ACCESS_KEY': 'private', 'PAYU_CLIENT_SECRET': 'private',
              'WP_CHECKOUT_KEY_FILE': '/private/key', 'PYTHONPATH': '/untrusted',
              'WP_ENABLE_FUTURE_NETWORK_SERVICE': '1'}
    original = dict(source)
    env = demo_environment(source, tmp_path/'local.sqlite3')
    assert env['PATH'] == source['PATH']
    assert env['WP_ENABLE_PRODUCT_UNITS'] == '1'
    assert set(env).intersection(source) == {'PATH', 'WP_ENABLE_PRODUCT_UNITS'}
    assert source == original


def test_demo_serves_web_ui_and_assets():
    from fastapi.testclient import TestClient
    from backend.app import app
    client = TestClient(app)
    page = client.get('/')
    assert page.status_code == 200
    assert 'ŚRODOWISKO TESTOWE' in page.text
    for asset in ('app.js', 'dashboard.js', 'style.css'):
        result = client.get('/assets/' + asset)
        assert result.status_code == 200
        assert len(result.content) > 100

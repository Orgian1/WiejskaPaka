"""Testy izolacji podglądu UI i serwowania strony."""
from pathlib import Path
from unittest.mock import patch

from scripts.run_phone_demo import demo_environment, main


def test_demo_environment_drops_external_database_config():
    source = {'DATABASE_URL': 'postgresql://example.invalid/production',
              'WP_TEST_DATABASE_URL': 'postgresql://example.invalid/test',
              'WP_TEST_POSTGRES_DSN': 'secret',
              'WP_ALLOW_REMOTE_DISPOSABLE_TEST_DB': 'YES_I_CONFIRM',
              'PATH': '/usr/bin'}
    result = demo_environment(source, Path('/tmp/isolated_demo.sqlite3'))
    assert all(key not in result for key in source if key.startswith(('DATABASE_URL', 'WP_TEST_', 'WP_ALLOW_')))
    assert Path(result['WIEJSKAPAKA_DB']) == Path('/tmp/isolated_demo.sqlite3')
    assert result['PATH'] == '/usr/bin'


def test_demo_launcher_binds_only_to_loopback():
    with patch('scripts.run_phone_demo.subprocess.call', return_value=0) as runner:
        assert main(['--port', '8766']) == 0
    command = runner.call_args.args[0]
    assert command[command.index('--host') + 1] == '127.0.0.1'
    assert command[command.index('--port') + 1] == '8766'
    assert 'DATABASE_URL' not in runner.call_args.kwargs['env']


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

from pathlib import Path
from unittest.mock import patch

import pytest

from scripts.check_demo_readiness import check_ui, run_checks


class Response:
    def __init__(self, status_code=200, text=''):
        self.status_code = status_code
        self.text = text
        self.content = text.encode()


class Client:
    def __init__(self, missing=None):
        self.missing = missing

    def get(self, path):
        if path == '/':
            return Response(text=('lang="pl" name="viewport" ŚRODOWISKO TESTOWE '
                                  'id="auth" id="products" id="orders-section" id="dashboard"'))
        if path == '/assets/' + str(self.missing):
            return Response(status_code=404)
        return Response(text='ok')


def test_readiness_checks_ui_and_assets():
    assert check_ui(Client())


def test_readiness_rejects_missing_asset():
    with pytest.raises(AssertionError, match='Niedostępny zasób'):
        check_ui(Client(missing='app.js'))


def test_readiness_runs_isolated_subprocess_without_neon():
    source = {'DATABASE_URL': 'postgresql://example.invalid/production', 'PATH': '/usr/bin'}
    with patch('scripts.check_demo_readiness.subprocess.run') as runner:
        runner.return_value.returncode = 0
        assert run_checks(source) == 0
    kwargs = runner.call_args.kwargs
    assert 'DATABASE_URL' not in kwargs['env']
    assert kwargs['env']['WIEJSKAPAKA_DB'].endswith('ui_check.sqlite3')
    assert kwargs['cwd'] == Path(__file__).resolve().parents[1]

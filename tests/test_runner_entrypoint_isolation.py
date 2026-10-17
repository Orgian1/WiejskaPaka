"""Exercise diagnostic entrypoints with synthetic hostile parent configuration."""
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest


SENSITIVE = ('DATABASE_URL', 'NEON_DATABASE_URL', 'WP_TEST_DATABASE_URL',
             'WP_TEST_POSTGRES_DSN', 'WP_CHECKOUT_KEY_FILE',
             'WP_ALLOW_REMOTE_DISPOSABLE_TEST_DB', 'PGPASSWORD', 'PGSERVICE')

PROBE = '''import os, sqlite3
from pathlib import Path
def test_disposable_process():
    forbidden = %r
    assert not any(name in os.environ for name in forbidden)
    assert os.environ['PYTHONUTF8'] == '1'
    database = Path(os.environ['WIEJSKAPAKA_DB'])
    assert database.name == 'isolated.sqlite3'
    connection = sqlite3.connect(database)
    try:
        connection.execute('CREATE TABLE marker (id INTEGER PRIMARY KEY)')
        connection.execute('INSERT INTO marker VALUES (1)')
        connection.commit()
    finally:
        connection.close()
''' % (SENSITIVE,)


@pytest.mark.parametrize('entrypoint', ['run_isolated_pytest', 'run_http_acceptance_suite',
                                      'run_security_focus_isolated'])
def test_entrypoints_do_not_inherit_external_database_or_key(tmp_path, monkeypatch, entrypoint):
    module = importlib.import_module('scripts.' + entrypoint)
    root = tmp_path / 'project'
    (root / 'tests').mkdir(parents=True)
    (root / 'scripts').mkdir()
    files = []
    for suffix in ('one', 'two'):
        case = root / 'tests' / ('test_' + suffix + '.py')
        case.write_text(PROBE, encoding='utf-8')
        files.append(case)
    for key in SENSITIVE:
        monkeypatch.setenv(key, 'synthetic-parent-setting')
    monkeypatch.setenv('WIEJSKAPAKA_DB', str(tmp_path / 'must-not-be-used.sqlite3'))
    monkeypatch.setenv('PYTHONUTF8', '0')
    before = {key: os.environ[key] for key in SENSITIVE}
    output = root / 'result.json'
    monkeypatch.setattr(sys, 'argv', [entrypoint, '--output', str(output)])
    if entrypoint == 'run_isolated_pytest':
        monkeypatch.setattr(module, '__file__', str(root / 'scripts' / (entrypoint + '.py')))
    elif entrypoint == 'run_http_acceptance_suite':
        monkeypatch.setattr(module, 'ROOT', root)
        # Commands run real Python children, with no backend or network import.
        command = "import runpy; runpy.run_path({!r})['test_disposable_process']()"
        monkeypatch.setattr(module, 'TASKS', [
            (case.stem, [sys.executable, '-c', command.format(str(case))]) for case in files])
    else:
        monkeypatch.setattr(module, 'ROOT', root)
        monkeypatch.setattr(module, 'REPORT', output)
        monkeypatch.setattr(module, 'FILES', [case.relative_to(root).as_posix() for case in files])
        monkeypatch.setattr(module, 'FINGERPRINT_PATHS', [])
        monkeypatch.setattr(sys, 'argv', [entrypoint])
    assert module.main() == 0
    result = json.loads(output.read_text(encoding='utf-8'))
    entries = result.get('results', result.get('tasks'))
    assert len(entries) == 2
    assert not (tmp_path / 'must-not-be-used.sqlite3').exists()
    assert {key: os.environ[key] for key in SENSITIVE} == before


def test_diagnostic_timeout_is_a_failed_completed_attempt(tmp_path, monkeypatch):
    from scripts import run_isolated_pytest as module
    (tmp_path / 'tests').mkdir()
    (tmp_path / 'tests/test_one.py').write_text('def test_one(): pass\n')
    monkeypatch.setattr(module, '__file__', str(tmp_path / 'scripts/runner.py'))
    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(['synthetic-test'], 1)
    monkeypatch.setattr(module.subprocess, 'run', timeout)
    report = tmp_path / 'result.json'
    assert module.main(['--timeout', '1', '--output', str(report)]) == 1
    data = json.loads(report.read_text(encoding='utf-8'))
    assert data['complete'] and not data['success'] and data['passed'] == 0
    assert data['results'][0]['error'] == 'TimeoutExpired'


def test_acceptance_cannot_pass_an_empty_task_list(tmp_path, monkeypatch):
    from scripts import run_http_acceptance_suite as module
    monkeypatch.setattr(module, 'ROOT', tmp_path)
    monkeypatch.setattr(module, 'TASKS', [])
    assert module.main(['--output', 'result.json']) == 1
    data = json.loads((tmp_path / 'result.json').read_text(encoding='utf-8'))
    assert not data['passed']


def test_acceptance_source_change_invalidates_result(tmp_path, monkeypatch):
    from scripts import run_http_acceptance_suite as module
    monkeypatch.setattr(module, 'ROOT', tmp_path)
    monkeypatch.setattr(module, 'TASKS', [('synthetic', ['unused'])])
    (tmp_path / 'scripts').mkdir()
    def changed(*args, **kwargs):
        (tmp_path / 'scripts/change.py').write_text('CHANGED = True\n')
        return SimpleNamespace(returncode=0, stdout='', stderr='')
    monkeypatch.setattr(module.subprocess, 'run', changed)
    assert module.main(['--output', 'result.json']) == 1
    data = json.loads((tmp_path / 'result.json').read_text(encoding='utf-8'))
    assert not data['complete'] and not data['sources_unchanged'] and not data['passed']


def test_security_checkpoint_cannot_certify_sources_changed_during_run(tmp_path, monkeypatch):
    from scripts import run_security_focus_isolated as module
    (tmp_path / 'tests').mkdir()
    case = tmp_path / 'tests/test_one.py'
    case.write_text('def test_one(): pass\n')
    monkeypatch.setattr(module, 'ROOT', tmp_path)
    monkeypatch.setattr(module, 'REPORT', tmp_path / 'result.json')
    monkeypatch.setattr(module, 'FILES', ['tests/test_one.py'])
    monkeypatch.setattr(module, 'FINGERPRINT_PATHS', [])
    def changed(*args, **kwargs):
        case.write_text('def test_one(): assert False\n')
        return SimpleNamespace(returncode=0, stdout='', stderr='')
    monkeypatch.setattr(module.subprocess, 'run', changed)
    assert module.main() == 1
    data = json.loads(module.REPORT.read_text(encoding='utf-8'))
    assert not data['complete'] and not data['success'] and not data['sources_unchanged']
    assert data['results'][0]['status'] == 'STALE'


def test_security_checkpoint_is_invalidated_by_a_new_runtime_source(tmp_path, monkeypatch):
    from scripts import run_security_focus_isolated as module
    (tmp_path / 'tests').mkdir()
    (tmp_path / 'tests/test_one.py').write_text('def test_one(): pass\n')
    monkeypatch.setattr(module, 'ROOT', tmp_path)
    monkeypatch.setattr(module, 'REPORT', tmp_path / 'result.json')
    monkeypatch.setattr(module, 'FILES', ['tests/test_one.py'])
    monkeypatch.setattr(module, 'FINGERPRINT_PATHS', [])
    calls = []
    def passed(*args, **kwargs):
        calls.append(True)
        return SimpleNamespace(returncode=0, stdout='', stderr='')
    monkeypatch.setattr(module.subprocess, 'run', passed)
    assert module.main() == 0
    assert module.main() == 0
    assert len(calls) == 1
    (tmp_path / 'web').mkdir()
    (tmp_path / 'web/new.js').write_text('const changed = true;\n')
    assert module.main() == 0
    assert len(calls) == 2
    data = json.loads(module.REPORT.read_text(encoding='utf-8'))
    assert not data['results'][0]['reused_from_checkpoint']


def test_diagnostic_rejects_a_test_rewritten_during_execution(tmp_path, monkeypatch):
    from scripts import run_isolated_pytest as module
    (tmp_path / 'tests').mkdir()
    case = tmp_path / 'tests/test_one.py'
    case.write_text('def test_one(): pass\n')
    monkeypatch.setattr(module, '__file__', str(tmp_path / 'scripts/runner.py'))
    def changed(*args, **kwargs):
        case.write_text('def test_one(): assert False\n')
        return SimpleNamespace(returncode=0, stdout='', stderr='')
    monkeypatch.setattr(module.subprocess, 'run', changed)
    assert module.main(['--output', 'result.json']) == 1
    data = json.loads((tmp_path / 'result.json').read_text(encoding='utf-8'))
    assert not data['complete'] and not data['success'] and not data['sources_unchanged']

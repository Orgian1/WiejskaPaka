"""Regresje zabezpieczenia uruchamiania pełnego zestawu testów."""
from pathlib import Path
from scripts.run_tests_isolated import test_environment as make_env, main


def test_runner_removes_external_database_credentials():
    original = {
        'DATABASE_URL': 'postgresql://production.example/neondb',
        'WP_TEST_POSTGRES_DSN': 'postgresql://remote/test',
        'WP_TEST_DATABASE_URL': 'postgresql://remote/test',
        'WP_ALLOW_REMOTE_DISPOSABLE_TEST_DB': 'YES_I_CONFIRM',
        'WIEJSKAPAKA_DB': '/tmp/old.sqlite3',
        'SAFE_KEY': 'preserved',
    }
    env = make_env(original, Path('/tmp/fresh.sqlite3'))
    assert Path(env['WIEJSKAPAKA_DB']) == Path('/tmp/fresh.sqlite3')
    assert env['SAFE_KEY'] == 'preserved'
    assert all(k not in env for k in (
        'DATABASE_URL', 'WP_TEST_POSTGRES_DSN', 'WP_TEST_DATABASE_URL',
        'WP_ALLOW_REMOTE_DISPOSABLE_TEST_DB'))
    assert original['DATABASE_URL'].startswith('postgresql://')


def test_runner_invokes_pytest_in_temporary_directory(monkeypatch):
    calls = []

    def fake_call(cmd, cwd, env):
        assert cmd[1:3] == ['-m', 'pytest']
        assert cmd[3:] == ['-q', 'tests/test_stage4.py']
        assert Path(env['WIEJSKAPAKA_DB']).parent.is_dir()
        assert 'DATABASE_URL' not in env
        calls.append(Path(env['WIEJSKAPAKA_DB']).parent)
        return 17

    monkeypatch.setattr('scripts.run_tests_isolated.subprocess.call', fake_call)
    monkeypatch.setenv('DATABASE_URL', 'postgresql://example/neondb')
    assert main(['-q', 'tests/test_stage4.py']) == 17
    assert len(calls) == 1
    assert not calls[0].exists()


def test_runner_enforces_utf8_without_mutating_parent():
    original = {'PYTHONUTF8': '0', 'PYTHONIOENCODING': 'cp1250'}
    env = make_env(original, Path('disposable.sqlite3'))
    assert env['PYTHONUTF8'] == '1'
    assert env['PYTHONIOENCODING'] == 'utf-8'
    assert original == {'PYTHONUTF8': '0', 'PYTHONIOENCODING': 'cp1250'}

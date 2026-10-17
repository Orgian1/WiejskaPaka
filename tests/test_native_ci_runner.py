"""CI control-plane tests use fake child processes, not native execution evidence."""
import json
from pathlib import Path
import subprocess

import pytest

from scripts import run_native_ci as ci

DSN = 'postgresql://ci:disposable@127.0.0.1:5432/wp_test_ci'
SENSITIVE = 'never-publish-this-value'


def junit(command, *, passed=15, skipped=0, failed=0):
    path = Path(command[command.index('--junitxml')+1])
    path.write_text('<testsuite>'+('<testcase/>'*passed)+
                    ('<testcase><skipped/></testcase>'*skipped)+
                    ('<testcase><failure>private</failure></testcase>'*failed)+'</testsuite>')


def source():
    return {'WP_TEST_POSTGRES_DSN': DSN, 'DATABASE_URL': SENSITIVE,
            'WP_CHECKOUT_KEY_FILE': SENSITIVE, 'CUSTOM_SECRET': SENSITIVE,
            'PGSERVICE': SENSITIVE, 'GITHUB_TOKEN': SENSITIVE, 'WP_ENV': 'production'}


@pytest.mark.parametrize('dsn', [None, 'postgresql://a:b@example.invalid/wp_test_ci',
    'postgresql://a:b@127.0.0.1/production',
    'postgresql://a:b@127.0.0.1/wp_test_ci?host=example.invalid'])
def test_postgres_requires_unambiguous_disposable_loopback_database(tmp_path, dsn):
    def forbidden(*args, **kwargs):
        pytest.fail('Unsafe database must not launch a process')
    result = ci.run('postgres', tmp_path/'result.json', source={'WP_TEST_POSTGRES_DSN': dsn}, runner=forbidden)
    assert not result['success'] and not result['complete'] and not result['tasks']


def test_postgres_environment_and_report_do_not_forward_secrets(tmp_path):
    def runner(command, **kwargs):
        env = kwargs['env']
        assert not {'DATABASE_URL', 'WP_CHECKOUT_KEY_FILE', 'CUSTOM_SECRET', 'PGSERVICE', 'GITHUB_TOKEN'} & env.keys()
        assert env['WP_TEST_DATABASE_URL'] == env['WP_TEST_POSTGRES_DSN'] == DSN
        assert env['WP_ENV'] == 'test'
        junit(command)
        return subprocess.CompletedProcess(command, 0, SENSITIVE, SENSITIVE)
    path = tmp_path/'result.json'
    result = ci.run('postgres', path, source=source(), runner=runner)
    assert result['success'] and result['tasks'][0]['test_counts']['passed'] == 15
    assert SENSITIVE not in path.read_text() and DSN not in path.read_text()


@pytest.mark.parametrize('variant', ['skip', 'failure', 'empty', 'too-few', 'missing', 'malformed', 'timeout', 'launch-error'])
def test_native_gate_cannot_pass_incomplete_or_failed_results(tmp_path, variant):
    def runner(command, **kwargs):
        if variant == 'timeout':
            raise subprocess.TimeoutExpired(command, 600, output=SENSITIVE, stderr=SENSITIVE)
        if variant == 'launch-error':
            raise OSError(SENSITIVE)
        if variant == 'malformed':
            Path(command[-1]).write_text(SENSITIVE)
        elif variant != 'missing':
            junit(command, passed=0 if variant=='empty' else 1 if variant=='too-few' else 15,
                  skipped=int(variant=='skip'), failed=int(variant=='failure'))
        return subprocess.CompletedProcess(command, 0, SENSITIVE, SENSITIVE)
    path = tmp_path/'result.json'
    result = ci.run('postgres', path, source=source(), runner=runner)
    assert not result['success']
    assert SENSITIVE not in path.read_text()


def test_windows_gate_does_not_claim_linux_is_windows(tmp_path, monkeypatch):
    monkeypatch.setattr(ci.platform, 'system', lambda: 'Linux')
    def forbidden(*args, **kwargs):
        pytest.fail('Not a Windows runner')
    result = ci.run('windows', tmp_path/'result.json', source={}, runner=forbidden)
    assert not result['success'] and result['error'] == 'WINDOWS_REQUIRED'


@pytest.mark.parametrize('variant', ['valid', 'incomplete', 'changed', 'bad-counts', 'missing-modules'])
def test_windows_requires_a_complete_consistent_isolated_report(tmp_path, monkeypatch, variant):
    monkeypatch.setattr(ci.platform, 'system', lambda: 'Windows')
    def runner(command, **kwargs):
        data = {'complete': variant!='incomplete', 'success': True, 'sources_unchanged': variant!='changed',
                'executed': 1, 'planned': 2 if variant=='missing-modules' else 1,
                'test_counts': {'total': 28 if variant=='bad-counts' else 27, 'passed': 10,
                                'failed': 0, 'skipped': 17, 'secret': SENSITIVE},
                'output_tail': SENSITIVE}
        Path(command[-1]).write_text(json.dumps(data))
        return subprocess.CompletedProcess(command, 0, SENSITIVE, SENSITIVE)
    path = tmp_path/'result.json'
    result = ci.run('windows', path, source=source(), runner=runner)
    assert result['success'] == (variant == 'valid')
    assert SENSITIVE not in path.read_text()


@pytest.mark.parametrize('http_code', [0, 1])
def test_browser_requires_offline_and_real_http_tasks(tmp_path, http_code):
    calls = []
    def runner(command, **kwargs):
        calls.append(command)
        assert kwargs['env']['WIEJSKAPAKA_EXTENDED_BROWSER'] == '1'
        if '--junitxml' in command:
            junit(command, passed=7)
            return subprocess.CompletedProcess(command, 0, '', '')
        return subprocess.CompletedProcess(command, http_code, SENSITIVE, SENSITIVE)
    result = ci.run('browser', tmp_path/'result.json', source=source(), runner=runner)
    assert len(calls) == 2 and result['success'] == (http_code == 0)


def test_browser_skip_prevents_http_and_green_gate(tmp_path):
    calls = []
    def runner(command, **kwargs):
        calls.append(command)
        junit(command, passed=6, skipped=1)
        return subprocess.CompletedProcess(command, 0, '', '')
    result = ci.run('browser', tmp_path/'result.json', source={}, runner=runner)
    assert len(calls) == 1 and not result['success'] and not result['complete']


def test_source_change_invalidates_native_evidence(tmp_path, monkeypatch):
    values = iter([{'runtime_sha256': 'before'}, {'runtime_sha256': 'after'}])
    monkeypatch.setattr(ci, 'evidence', lambda root: next(values))
    def runner(command, **kwargs):
        junit(command)
        return subprocess.CompletedProcess(command, 0, '', '')
    result = ci.run('postgres', tmp_path/'result.json', source=source(), runner=runner)
    assert not result['success'] and not result['sources_unchanged']

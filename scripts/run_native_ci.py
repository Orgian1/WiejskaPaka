"""Fail-closed CI gates; publish counts, never captured logs or credentials."""
import argparse
import hashlib
import json
import os
import platform
import re
from pathlib import Path
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

from backend.postgres_test_guard import require_disposable_postgres
from scripts.regression_manifest import application_fingerprint, manifest
from scripts.run_tests_isolated import test_environment as isolated_environment

ROOT = Path(__file__).resolve().parents[1]
POSTGRES_TESTS = ('test_postgres_environment.py', 'test_postgres_transaction_integration_optional.py',
                  'test_postgres_full_api_optin.py')
RECOVERY_TESTS = ('test_sample_demo.py', 'test_sample_demo_launcher.py', 'test_seller_payout_ui.py', 'test_seller_settlement_ui.py', 'test_admin_seller_review.py', 'test_encrypted_sqlite_snapshot.py', 'test_sqlite_snapshot.py', 'test_sqlite_recovery_rehearsal.py',
                  'test_password_reset_http.py')
BROWSER_TESTS = ('test_preview_credentials.py', 'test_catalog_page_browser.py', 'test_support_cases_browser.py', 'test_sample_demo_browser.py', 'test_admin_seller_review_browser.py', 'test_seller_compliance_browser.py', 'test_mobile_offline.py', 'test_roles_offline.py', 'test_password_reset_browser.py')
SYSTEM_ENV = ('PATH', 'SYSTEMROOT', 'WINDIR', 'SYSTEMDRIVE', 'COMSPEC', 'PATHEXT',
              'USERPROFILE', 'LOCALAPPDATA', 'APPDATA', 'PROGRAMDATA', 'PROGRAMFILES',
              'PROGRAMFILES(X86)', 'TEMP', 'TMP', 'TMPDIR', 'LANG', 'LC_ALL',
              'PLAYWRIGHT_BROWSERS_PATH')


def evidence(root):
    digest = hashlib.sha256()
    for name in ('requirements.txt', 'requirements-lock.txt'):
        digest.update(name.encode())
        digest.update((root / name).read_bytes())
    tests = hashlib.sha256()
    for path in sorted((root / 'tests').rglob('*.py')):
        tests.update(path.relative_to(root).as_posix().encode())
        tests.update(hashlib.sha256(path.read_bytes()).digest())
    workflow = root / '.github/workflows/native-tests.yml'
    return {'runtime_sha256': application_fingerprint(root), 'tests_sha256': manifest(root)['sha256'],
            'test_sources_sha256': tests.hexdigest(), 'dependencies_sha256': digest.hexdigest(),
            'workflow_sha256': hashlib.sha256(workflow.read_bytes()).hexdigest() if workflow.is_file() else None}


def counts(path):
    cases = list(ET.parse(path).getroot().iter('testcase'))
    failed = sum(c.find('failure') is not None or c.find('error') is not None for c in cases)
    skipped = sum(c.find('skipped') is not None for c in cases)
    return {'total': len(cases), 'passed': len(cases)-failed-skipped, 'failed': failed, 'skipped': skipped}



def failure_locations(path, root):
    """Return only allowlisted repository filenames and line numbers, never logs."""
    known = {p.name for p in (Path(root)/'tests').glob('test_*.py')}
    found = set()
    for case in ET.parse(path).getroot().iter('testcase'):
        for tag in ('failure', 'error'):
            failure = case.find(tag)
            if failure is None:
                continue
            # Do not emit assertion text, parameter values, absolute paths or locals.
            for name, line in re.findall(r'(?:^|[/\\ ])(test_[A-Za-z0-9_]+\.py):(\d+):',
                                         failure.text or '', re.MULTILINE):
                if name in known:
                    found.add((name, int(line)))
    return [{'file': name, 'line': line} for name,line in sorted(found)[:30]]


def checked_counts(data):
    if not isinstance(data, dict):
        raise ValueError('Missing or invalid counts')
    result = {key: data[key] for key in ('total', 'passed', 'failed', 'skipped')}
    if (any(type(value) is not int or value < 0 for value in result.values())
            or result['total'] != sum(result[key] for key in ('passed', 'failed', 'skipped'))):
        raise ValueError('Invalid counts')
    return result


def run(gate, report, *, root=ROOT, source=None, runner=subprocess.run):
    root = Path(root).resolve()
    before = evidence(root)
    result = {'gate': gate, 'complete': False, 'success': False, 'sources_unchanged': False,
              'system': platform.system(), 'evidence': before, 'tasks': []}
    with tempfile.TemporaryDirectory(prefix='wp_native_ci_') as folder:
        folder = Path(folder)
        source = dict(os.environ if source is None else source)
        env = isolated_environment({key: source[key] for key in SYSTEM_ENV if key in source}, folder / 'unused.sqlite')
        # Never inherit a production mode or externally supplied demo-data path.
        env['WP_ENV'] = 'test'
        env['WP_ENABLE_TEST_PAYMENTS'] = '1'
        env.pop('WIEJSKAPAKA_EXTENDED_BROWSER', None)
        tasks = []
        raw = folder / 'raw.json'
        xml = folder / 'cases.xml'
        if gate in ('windows', 'windows-recovery'):
            if platform.system() != 'Windows':
                result['error'] = 'WINDOWS_REQUIRED'
            else:
                tasks = [('windows_recovery', [sys.executable, '-m', 'pytest', '-q',
                    *[str(root/'tests'/name) for name in RECOVERY_TESTS], '--junitxml', str(xml)], 'junit'),
                         ('isolated_regression', [sys.executable, str(root/'scripts/run_tests_per_file.py'), '--report', str(raw)], 'full')]
                if gate == 'windows-recovery':
                    tasks = tasks[:1]
        elif gate == 'postgres':
            dsn = source.get('WP_TEST_POSTGRES_DSN')
            try:
                require_disposable_postgres(dsn, environ={})
            except ValueError:
                result['error'] = 'UNSAFE_OR_MISSING_TEST_DATABASE'
            else:
                env.update(WP_TEST_POSTGRES_DSN=dsn, WP_TEST_DATABASE_URL=dsn)
                tasks = [('native_postgres', [sys.executable, '-m', 'pytest', '-q',
                    *[str(root/'tests'/name) for name in POSTGRES_TESTS], '--junitxml', str(xml)], 'junit')]
        elif gate == 'browser':
            env['WIEJSKAPAKA_EXTENDED_BROWSER'] = '1'
            tasks = [('offline_browser', [sys.executable, '-m', 'pytest', '-q',
                    *[str(root/'tests'/name) for name in BROWSER_TESTS], '--junitxml', str(xml)], 'junit'),
                     ('http_viewports', [sys.executable, '-m', 'scripts.check_mobile_browser'], 'exit')]
        else:
            raise ValueError('Unknown CI gate')
        for name, command, kind in tasks:
            task = {'name': name, 'success': False}
            try:
                process = runner(command, cwd=root, env=env, capture_output=True,
                                 text=True, encoding='utf-8', timeout=1500 if kind=='full' else 600)
                task['returncode'] = process.returncode
                if kind == 'full':
                    data = json.loads(raw.read_text(encoding='utf-8'))
                    if not isinstance(data, dict) or not isinstance(data.get('results', []), list):
                        raise ValueError('Invalid isolated report')
                    known = {p.name for p in (root/'tests').glob('test_*.py')}
                    entries = [entry for entry in data.get('results', []) if isinstance(entry, dict)
                               and isinstance(entry.get('file'), str) and entry['file'] in known]
                    task['failed_modules'] = sorted({entry['file'] for entry in entries
                        if entry.get('returncode') != 0})
                    task['incomplete_modules'] = sorted({entry['file'] for entry in entries
                        if entry.get('test_counts') is None})
                    task['timed_out_modules'] = sorted({entry['file'] for entry in entries
                        if entry.get('timeout') is True})
                    task['test_counts'] = checked_counts(data['test_counts'])
                    task['success'] = bool(process.returncode == 0 and data['complete'] is True and
                        data['success'] is True and data['sources_unchanged'] is True
                        and data['executed'] == data['planned'] and data['planned'] > 0
                        and task['test_counts']['total'] > 0 and task['test_counts']['failed'] == 0)
                elif kind == 'junit':
                    task['test_counts'] = counts(xml)
                    task['failure_locations'] = failure_locations(xml, root)
                    c = task['test_counts']
                    minimum = 42 if gate == 'postgres' else 80 if gate in ('windows', 'windows-recovery') else 36
                    task['success'] = process.returncode == 0 and c['total'] >= minimum and c['failed'] == 0 and c['skipped'] == 0
                else:
                    task['success'] = process.returncode == 0
            except subprocess.TimeoutExpired:
                task['error'] = 'TIMEOUT'
            except OSError:
                task['error'] = 'PROCESS_OR_RESULT_UNAVAILABLE'
            except (ValueError, KeyError, ET.ParseError):
                task['error'] = 'INVALID_TEST_RESULT'
            result['tasks'].append(task)
            print(f"{gate}/{name}: {'PASS' if task['success'] else 'FAIL'}", flush=True)
            if not task['success']:
                break
        result['complete'] = bool(tasks) and len(result['tasks']) == len(tasks)
    result['sources_unchanged'] = before == evidence(root)
    result['success'] = result['complete'] and result['sources_unchanged'] and all(t['success'] for t in result['tasks'])
    report = Path(report)
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('gate', choices=('windows', 'windows-recovery', 'postgres', 'browser'))
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    result = run(args.gate, args.report)
    print(args.gate + ': ' + ('PASS' if result['success'] else 'FAIL'))
    return 0 if result['success'] else 1


if __name__ == '__main__':
    raise SystemExit(main())

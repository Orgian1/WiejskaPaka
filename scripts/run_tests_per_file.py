"""Run each pytest module in a fresh subprocess and SQLite database.

This prevents module-level environment settings and app imports leaking between
unrelated test modules. No remote DB credentials are forwarded to children.
"""
import argparse
import hashlib
import json
import os
import re
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET

from run_tests_isolated import test_environment
from run_regression_chunks import write_report_atomic


def application_fingerprint(root):
    """Fingerprint runtime sources; cached PASS cannot outlive an application change."""
    digest = hashlib.sha256()
    for folder in ('backend', 'web', 'database', 'scripts'):
        base = root / folder
        if not base.is_dir():
            continue
        for path in sorted(base.rglob('*')):
            if path.is_file() and path.suffix in ('.py', '.js', '.sql', '.html', '.css'):
                digest.update(path.relative_to(root).as_posix().encode('utf-8'))
                digest.update(hashlib.sha256(path.read_bytes()).digest())
    for name in ('requirements.txt','requirements-lock.txt'):
        path=root/name
        if path.is_file():
            digest.update(name.encode('utf-8'))
            digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def testcase_counts(path):
    if not Path(path).is_file():
        return None
    cases = list(ET.parse(path).getroot().iter('testcase'))
    failed = sum(case.find('failure') is not None or case.find('error') is not None for case in cases)
    skipped = sum(case.find('skipped') is not None for case in cases)
    return {'total': len(cases), 'passed': len(cases) - failed - skipped,
            'failed': failed, 'skipped': skipped}


def failure_locations(path, root):
    """Preserve allowlisted source locations before deleting private JUnit XML."""
    if not Path(path).is_file():return []
    known={p.name for p in (Path(root)/'tests').glob('test_*.py')}
    found=set()
    for case in ET.parse(path).getroot().iter('testcase'):
        for tag in ('failure','error'):
            node=case.find(tag)
            if node is None or not isinstance(node.text,str):continue
            for name,line in re.findall(r'(?:^|[/\\ ])(test_[A-Za-z0-9_]+\.py):(\d{1,7}):',node.text,re.MULTILINE):
                if name in known and int(line)>0:found.add((name,int(line)))
    return [{'file':name,'line':line} for name,line in sorted(found)[:30]]


def run(root, *, selected=None, timeout=90, report=None, resume=False, refresh_stale=False):
    root = Path(root).resolve()
    if timeout < 1:
        raise ValueError('timeout must be positive')
    files = sorted((root / 'tests').glob('test_*.py')) if selected is None else [Path(p) for p in selected]
    if not files:
        raise ValueError('No test files found')
    for path in files:
        resolved = path.resolve()
        if (resolved.parent != root / 'tests' or path.is_symlink() or
                not resolved.is_file() or not resolved.name.startswith('test_') or resolved.suffix != '.py'):
            raise ValueError('Only regular test modules inside tests/ are accepted')
    fingerprint = application_fingerprint(root)
    initial_tests = {p.resolve(): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    previous = {}
    if resume:
        if report is None or not Path(report).is_file():
            raise ValueError('Resume requires an existing report')
        old = json.loads(Path(report).read_text(encoding='utf-8'))
        if old.get('application_sha256') != fingerprint:
            if not refresh_stale:
                raise ValueError('Application sources changed since the previous regression report')
            old['results'] = []  # Never reuse PASS from different application code.
        old_results = old.get('results')
        if not isinstance(old_results, list) or old.get('planned') != len(files):
            raise ValueError('Resume report does not match current test plan')
        expected_names = [p.name for p in files]
        recorded_names = [item.get('file') for item in old_results]
        if recorded_names != expected_names[:len(recorded_names)]:
            raise ValueError('Resume report has unexpected, reordered or duplicate modules')
        for item, path in zip(old_results, files):
            if item.get('sha256') != hashlib.sha256(path.read_bytes()).hexdigest():
                if refresh_stale:
                    continue  # Re-run changed module; never reuse stale evidence.
                raise ValueError(f'Stale test module in resume report: {path.name}')
            previous[path.name] = item
    results = []
    for path in files:
        resolved = path.resolve()
        if (resolved.parent != root / 'tests' or path.is_symlink() or
                not resolved.is_file() or not resolved.name.startswith('test_') or resolved.suffix != '.py'):
            raise ValueError('Only regular test modules inside tests/ are accepted')
        if resolved.name in previous and previous[resolved.name].get('returncode') == 0:
            results.append(previous[resolved.name])
            print(f'{resolved.name}: REUSED PASS', flush=True)
            continue
        with tempfile.TemporaryDirectory(prefix='wiejskapaka_file_') as tmp:
            env = test_environment(os.environ, Path(tmp) / 'isolated.sqlite3')
            junit = Path(tmp) / 'junit.xml'
            started = time.monotonic()
            try:
                proc = subprocess.run([sys.executable, '-m', 'pytest', '-q', '--disable-warnings',
                                       '--junitxml', str(junit), str(resolved)],
                                      cwd=root, env=env, capture_output=True, text=True, encoding='utf-8', timeout=timeout)
                entry = {'file': resolved.name, 'sha256': hashlib.sha256(resolved.read_bytes()).hexdigest(), 'returncode': proc.returncode,
                         'seconds': round(time.monotonic() - started, 2),
                         'test_counts': testcase_counts(junit),
                         'failure_locations': failure_locations(junit,root),
                         'output_tail': (proc.stdout + proc.stderr)[-3000:]}
            except subprocess.TimeoutExpired as exc:
                entry = {'file': resolved.name, 'sha256': hashlib.sha256(resolved.read_bytes()).hexdigest(), 'returncode': None, 'timeout': True,
                         'seconds': round(time.monotonic() - started, 2),
                         'output_tail': str(exc)}
        results.append(entry)
        print(f"{resolved.name}: {'PASS' if entry['returncode'] == 0 else 'FAIL'}", flush=True)
        if report:
            write_report_atomic(report, {'application_sha256': fingerprint, 'complete': False, 'success': False,
                                         'executed': len(results), 'planned': len(files),
                                         'results': results})
    unchanged = (application_fingerprint(root) == fingerprint and all(
        path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == digest
        for path, digest in initial_tests.items()))
    success = unchanged and all(item['returncode'] == 0 for item in results)
    counts_complete = all(item.get('test_counts') is not None for item in results)
    counts = {key: sum(item['test_counts'][key] for item in results)
              for key in ('total', 'passed', 'failed', 'skipped')} if counts_complete else None
    if report:
        write_report_atomic(report, {'application_sha256': fingerprint, 'complete': unchanged, 'success': success,
                                     'sources_unchanged': unchanged,
                                     'invalid_reason': None if unchanged else 'sources_changed_during_run',
                                     'test_counts': counts,
                                     'executed': len(results), 'planned': len(files),
                                     'passed': sum(item['returncode'] == 0 for item in results),
                                     'failed': sum(item['returncode'] != 0 for item in results),
                                     'results': results})
    return 0 if success else 1


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('files', nargs='*')
    parser.add_argument('--timeout', type=int, default=90)
    parser.add_argument('--resume', action='store_true')
    parser.add_argument('--refresh-stale', action='store_true', help='Re-run changed tests rather than abort resume')
    parser.add_argument('--report', default='per_file_regression_report.json')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    return run(root, selected=[root / 'tests' / p for p in args.files] if args.files else None,
               timeout=args.timeout, report=root / args.report, resume=args.resume, refresh_stale=args.refresh_stale)


if __name__ == '__main__':
    raise SystemExit(main())

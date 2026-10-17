"""Run pytest modules in separate processes to expose import-time shared state.

This is a diagnostic runner, not a replacement for a full-suite regression.
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.run_tests_isolated import test_environment
from scripts.aggregate_full_regression import write_report_atomic
from scripts.regression_manifest import discover, application_fingerprint

def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--limit', type=int, default=0, help='Maximum modules; 0 = all')
    parser.add_argument('--output', default='isolated_pytest_results.json')
    parser.add_argument('--timeout', type=int, default=90)
    args = parser.parse_args(argv)
    if args.limit < 0 or args.timeout < 1:
        parser.error('Limit must be non-negative and timeout must be positive')
    root = Path(__file__).resolve().parents[1]
    modules = discover(root)
    if args.limit:
        modules = modules[:args.limit]
    results = []
    initial_tests = {module: hashlib.sha256(module.read_bytes()).hexdigest() for module in modules}
    fingerprint = application_fingerprint(root)
    output = root / args.output
    report = {'count': 0, 'planned': len(modules), 'passed': 0, 'complete': False,
              'success': False, 'application_sha256': fingerprint, 'results': results}
    write_report_atomic(output, report)
    for module in modules:
        with tempfile.TemporaryDirectory(prefix='wp_diagnostic_') as directory:
            env = test_environment(os.environ, Path(directory) / 'isolated.sqlite3')
            try:
                proc = subprocess.run([sys.executable, '-m', 'pytest', '-q', str(module)],
                                      cwd=root, env=env, capture_output=True, text=True,
                                      encoding='utf-8', timeout=args.timeout)
                item = {'module': module.name, 'passed': proc.returncode == 0,
                        'returncode': proc.returncode,
                        'tail': '\n'.join((proc.stdout + proc.stderr).splitlines()[-12:])}
            except (subprocess.TimeoutExpired, OSError) as exc:
                item = {'module': module.name, 'passed': False, 'returncode': None,
                        'error': type(exc).__name__}
        results.append(item)
        report.update(count=len(results), passed=sum(r['passed'] for r in results))
        write_report_atomic(output, report)
        print(('PASS' if item['passed'] else 'FAIL'), module.name, flush=True)
    report['sources_unchanged'] = application_fingerprint(root) == fingerprint and all(
        module.is_file() and not module.is_symlink() and hashlib.sha256(module.read_bytes()).hexdigest() == digest
        for module, digest in initial_tests.items())
    report['complete'] = report['sources_unchanged']
    report['success'] = report['complete'] and all(r['passed'] for r in results)
    write_report_atomic(output, report)
    return 0 if report['success'] else 1


if __name__ == '__main__':
    sys.exit(main())

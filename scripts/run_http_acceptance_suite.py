"""Powtarzalna kontrola lokalnego HTTP; bez Neon i produkcyjnych płatności."""
import argparse
import datetime as dt
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
from scripts.regression_manifest import application_fingerprint
TASKS = [
    ('http_loopback', [sys.executable, 'scripts/check_real_http_loopback.py']),
    ('http_checkout_delivery_refund', [sys.executable, 'scripts/check_http_checkout_e2e.py']),
    ('http_multi_seller_cart', [sys.executable, 'scripts/check_http_multi_seller_cart.py']),
    ('privacy_and_shipping_pytest', [sys.executable, '-m', 'pytest', '-q',
      'tests/test_b501_shared_delivery.py', 'tests/test_delivery_privacy_stage09.py',
      'tests/test_http_privacy_policy.py', 'tests/test_web_session_privacy.py']),
]

def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', default='RAPORT_HTTP_AKCEPTACJA.json')
    args = parser.parse_args(argv)
    fingerprint = application_fingerprint(ROOT)
    report = {'timestamp_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
              'scope': 'local HTTP, disposable SQLite, simulated payments; no PostgreSQL/Neon',
              'application_sha256': fingerprint, 'complete': False, 'passed': False,
              'tasks': []}
    output = ROOT / args.output
    write_report_atomic(output, report)
    for name, command in TASKS:
        try:
            with tempfile.TemporaryDirectory(prefix='wp_http_acceptance_') as directory:
                env = test_environment(os.environ, Path(directory) / 'isolated.sqlite3')
                result = subprocess.run(command, cwd=ROOT, env=env, text=True,
                                        encoding='utf-8', capture_output=True, timeout=150)
            item = {'name': name, 'passed': result.returncode == 0,
                    'returncode': result.returncode, 'output_tail': result.stdout[-3000:],
                    'error_tail': result.stderr[-1000:]}
        except subprocess.TimeoutExpired as exc:
            item = {'name': name, 'passed': False, 'error': 'timeout',
                    'output_tail': str(exc.stdout or b'')[-1000:]}
        except OSError as exc:
            item = {'name': name, 'passed': False, 'error': type(exc).__name__}
        report['tasks'].append(item)
        write_report_atomic(output, report)
        print(f"{name}: {'PASS' if item['passed'] else 'FAIL'}", flush=True)
    report['sources_unchanged'] = application_fingerprint(ROOT) == fingerprint
    report['complete'] = report['sources_unchanged']
    report['passed'] = bool(report['tasks']) and report['complete'] and all(task['passed'] for task in report['tasks'])
    write_report_atomic(output, report)
    return 0 if report['passed'] else 1

if __name__ == '__main__':
    raise SystemExit(main())

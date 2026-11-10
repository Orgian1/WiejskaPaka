"""Large reproducible LOCAL acceptance gate. Never reads remote database credentials.

Each subprocess is isolated; a failure is reported and fails the gate.
"""
import datetime as dt
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TASKS = [
    ('http_acceptance', [sys.executable, 'scripts/run_http_acceptance_suite.py', '--output', 'RAPORT_HTTP_AKCEPTACJA_DUZA_PACZKA.json'], 210),
    ('http_role_boundaries', [sys.executable, 'scripts/check_http_role_boundaries.py'], 90),
    ('isolated_b1681_checkout_idempotency', [sys.executable, '-m', 'pytest', '-q', 'tests/test_b1681_checkout_idempotency.py'], 90),
    ('isolated_b1801_concurrent_stock', [sys.executable, '-m', 'pytest', '-q', 'tests/test_b1801_concurrent_stock.py'], 90),
    ('isolated_b1921_per_seller_cart_limits', [sys.executable, '-m', 'pytest', '-q', 'tests/test_b1921_per_seller_cart_limits.py'], 90),
    ('isolated_b521_shipping_policy', [sys.executable, '-m', 'pytest', '-q', 'tests/test_b521_shipping_policy.py'], 90),
    ('isolated_b581_shipment_pin', [sys.executable, '-m', 'pytest', '-q', 'tests/test_b581_shipment_pin.py'], 90),
    ('isolated_b641_shipment_failure', [sys.executable, '-m', 'pytest', '-q', 'tests/test_b641_shipment_failure.py'], 90),
    ('isolated_b721_shipment_cancel', [sys.executable, '-m', 'pytest', '-q', 'tests/test_b721_shipment_cancel.py'], 90),
    ('isolated_b901_reconciliation', [sys.executable, '-m', 'pytest', '-q', 'tests/test_b901_reconciliation.py'], 25),
    ('javascript_syntax', ['node', '--check', 'web/app.js'], 15),
    ('python_compile', [sys.executable, '-m', 'compileall', '-q', 'backend', 'scripts'], 25),
]

def main():
    env = os.environ.copy()
    # Ensure the test environment cannot accidentally connect to a configured remote DB.
    for name in ('DATABASE_URL', 'NEON_DATABASE_URL', 'PGHOST', 'PGPASSWORD', 'PGSERVICE'):
        env.pop(name, None)
    old_path = ROOT / 'RAPORT_DUZA_PACZKA_LOKALNA.json'
    previous = json.loads(old_path.read_text(encoding='utf-8')) if old_path.exists() else {}
    already_passed = {row['name']: row for row in previous.get('tasks', []) if row.get('passed')}
    report = {'created_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
              'environment': 'local SQLite only; remote DB environment variables stripped',
              'tasks': []}
    for name, command, timeout in TASKS:
        if name in already_passed:
            report['tasks'].append(already_passed[name])
            print(f'{name}: PASS (saved)', flush=True)
            continue
        try:
            result = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, text=True, timeout=timeout)
            row = {'name': name, 'passed': result.returncode == 0, 'returncode': result.returncode,
                   'stdout_tail': result.stdout[-5000:], 'stderr_tail': result.stderr[-3000:]}
        except subprocess.TimeoutExpired as exc:
            row = {'name': name, 'passed': False, 'error': 'timeout', 'timeout_seconds': timeout,
                   'stdout_tail': str(exc.stdout or '')[-2000:]}
        report['tasks'].append(row)
        print(f"{name}: {'PASS' if row['passed'] else 'FAIL'}", flush=True)
        (ROOT / 'RAPORT_DUZA_PACZKA_LOKALNA.json').write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    report['passed'] = all(row['passed'] for row in report['tasks'])
    (ROOT / 'RAPORT_DUZA_PACZKA_LOKALNA.json').write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return 0 if report['passed'] else 1

if __name__ == '__main__':
    raise SystemExit(main())

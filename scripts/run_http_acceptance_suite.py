"""Powtarzalna kontrola lokalnego HTTP; bez Neon i produkcyjnych płatności."""
import argparse
import datetime as dt
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TASKS = [
    ('http_loopback', [sys.executable, 'scripts/check_real_http_loopback.py']),
    ('http_checkout_delivery_refund', [sys.executable, 'scripts/check_http_checkout_e2e.py']),
    ('http_multi_seller_cart', [sys.executable, 'scripts/check_http_multi_seller_cart.py']),
    ('privacy_and_shipping_pytest', [sys.executable, '-m', 'pytest', '-q',
      'tests/test_b501_shared_delivery.py', 'tests/test_delivery_privacy_stage09.py',
      'tests/test_http_privacy_policy.py', 'tests/test_web_session_privacy.py']),
]

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', default='RAPORT_HTTP_AKCEPTACJA.json')
    args = parser.parse_args()
    report = {'timestamp_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
              'scope': 'local HTTP, disposable SQLite, simulated payments; no PostgreSQL/Neon',
              'tasks': []}
    for name, command in TASKS:
        try:
            result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, timeout=150)
            item = {'name': name, 'passed': result.returncode == 0,
                    'returncode': result.returncode, 'output_tail': result.stdout[-3000:],
                    'error_tail': result.stderr[-1000:]}
        except subprocess.TimeoutExpired as exc:
            item = {'name': name, 'passed': False, 'error': 'timeout',
                    'output_tail': str(exc.stdout or b'')[-1000:]}
        report['tasks'].append(item)
        print(f"{name}: {'PASS' if item['passed'] else 'FAIL'}", flush=True)
    report['passed'] = all(task['passed'] for task in report['tasks'])
    (ROOT / args.output).write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return 0 if report['passed'] else 1

if __name__ == '__main__':
    raise SystemExit(main())

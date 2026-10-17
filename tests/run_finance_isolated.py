"""Run finance tests with a separate SQLite database and no remote credentials."""
from __future__ import annotations
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from run_tests_isolated import test_environment
from run_tests_per_file import testcase_counts

MODULES = [
    'test_b401_checkout.py', 'test_b481_multiseller_checkout.py',
    'test_b501_shared_delivery.py', 'test_b461_checkout_postgres_locking.py',
    'test_b1681_checkout_idempotency.py', 'test_b3241_checkout_session_races.py',
    'test_b3301_refresh_checkout_guard.py', 'test_b3361_direct_order_checkout_guard.py',
]

def main() -> int:
    results = []
    for module in MODULES:
        with tempfile.TemporaryDirectory(prefix='wp_finance_') as tmp:
            env = test_environment(os.environ, Path(tmp) / 'test.sqlite3')
            junit = Path(tmp) / 'results.xml'
            cmd = [sys.executable, '-m', 'pytest', '-q', '--junitxml', str(junit), f'tests/{module}']
            try:
                run = subprocess.run(cmd, cwd=ROOT, env=env, text=True,
                                     stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=90)
                result = {'module': module, 'exit_code': run.returncode,
                          'counts': testcase_counts(junit), 'output': run.stdout[-2500:]}
            except subprocess.TimeoutExpired:
                result = {'module': module, 'exit_code': -1, 'counts': None, 'output': 'TIMEOUT 90s'}
        results.append(result)
        print(f"{'PASS' if result['exit_code'] == 0 else 'FAIL'} {module}", flush=True)
    path = ROOT / 'finance_isolated_results.json'
    path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'Report: {path}')
    return int(any(item['exit_code'] != 0 for item in results))

if __name__ == '__main__':
    raise SystemExit(main())

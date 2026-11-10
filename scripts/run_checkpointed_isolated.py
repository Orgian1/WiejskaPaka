"""Checkpointed per-module regression, avoids import-time DB contamination.
Run: python scripts/run_checkpointed_isolated.py --limit 25 --timeout 90
"""
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--limit', type=int, default=0)
    p.add_argument('--timeout', type=int, default=90)
    p.add_argument('--report', default='isolated_checkpoint.json')
    a = p.parse_args()
    root = Path(__file__).resolve().parents[1]
    modules = sorted((root / 'tests').glob('test_*.py'))
    if a.limit:
        modules = modules[:a.limit]
    path = Path(a.report).resolve()
    records = []
    for m in modules:
        started = time.monotonic()
        try:
            r = subprocess.run([sys.executable, '-m', 'pytest', '-q', str(m)], cwd=root, capture_output=True, text=True, timeout=a.timeout)
            status = 'pass' if r.returncode == 0 else 'fail'
            detail = (r.stdout + '\n' + r.stderr)[-4000:]
        except subprocess.TimeoutExpired as e:
            status = 'timeout'
            detail = str(e)
        records.append({'module': m.name, 'status': status, 'duration_seconds': round(time.monotonic() - started, 2), 'tail': detail})
        path.write_text(json.dumps({'completed': len(records), 'total': len(modules), 'results': records}, indent=2, ensure_ascii=False), encoding='utf-8')
        print(status.upper(), m.name, flush=True)
    return 0 if all(r['status'] == 'pass' for r in records) else 1


if __name__ == '__main__':
    sys.exit(main())

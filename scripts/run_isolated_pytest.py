"""Run pytest modules in separate processes to expose import-time shared state.

This is a diagnostic runner, not a replacement for a full-suite regression.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--limit', type=int, default=0, help='Maximum modules; 0 = all')
    parser.add_argument('--output', default='isolated_pytest_results.json')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    modules = sorted((root / 'tests').glob('test_*.py'))
    if args.limit:
        modules = modules[:args.limit]
    results = []
    for module in modules:
        proc = subprocess.run([sys.executable, '-m', 'pytest', '-q', str(module)], cwd=root, capture_output=True, text=True)
        results.append({'module': module.name, 'passed': proc.returncode == 0, 'returncode': proc.returncode, 'tail': '\n'.join((proc.stdout + proc.stderr).splitlines()[-12:])})
        print(('PASS' if proc.returncode == 0 else 'FAIL'), module.name, flush=True)
    (root / args.output).write_text(json.dumps({'count': len(results), 'passed': sum(r['passed'] for r in results), 'results': results}, ensure_ascii=False, indent=2), encoding='utf-8')
    return int(any(not r['passed'] for r in results))


if __name__ == '__main__':
    sys.exit(main())

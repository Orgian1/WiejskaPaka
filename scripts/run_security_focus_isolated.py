"""Run security-sensitive pytest modules in individually isolated disposable SQLite DBs.

No production database credentials are inherited. JSON checkpoint after every module.
"""
import json
import hashlib
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / 'RAPORT_B_9841_10200_BEZPIECZENSTWO_IZOLACJA.json'
FINGERPRINT_PATHS = sorted((ROOT / 'backend').rglob('*.py')) + [ROOT / 'tests' / 'conftest.py', ROOT / 'scripts' / 'run_security_focus_isolated.py']

def fingerprint(file):
    digest = hashlib.sha256()
    for path in [ROOT / file, *FINGERPRINT_PATHS]:
        digest.update(str(path.relative_to(ROOT)).encode())
        if path.is_file():
            digest.update(path.read_bytes())
        else:
            digest.update(b'MISSING')
    return digest.hexdigest()

PATTERN = re.compile(r'auth|permission|privacy|payment|refund|postgres|delivery|shipment|security', re.I)
FILES = sorted(p.relative_to(ROOT).as_posix() for p in (ROOT / 'tests').glob('test_*.py') if PATTERN.search(p.name))

def main():
    prior = json.loads(REPORT.read_text()) if REPORT.exists() else {}
    done = {r['file']: r for r in prior.get('results', []) if r.get('status') == 'PASS' and r.get('fingerprint') == fingerprint(r['file'])}
    report = {'generated_utc': datetime.now(timezone.utc).isoformat(), 'scope': 'focused security and financial regression, per-module isolated SQLite', 'modules_total': len(FILES), 'results': []}
    for file in FILES:
        if file in done:
            row = done[file]
        else:
            with tempfile.TemporaryDirectory(prefix='wp_security_') as tmp:
                env = os.environ.copy()
                for key in list(env):
                    if key in {'DATABASE_URL', 'NEON_DATABASE_URL', 'WP_TEST_POSTGRES_DSN', 'WP_TEST_DATABASE_URL', 'WP_ALLOW_REMOTE_DISPOSABLE_TEST_DB', 'PGHOST', 'PGPASSWORD', 'PGSERVICE'}:
                        env.pop(key, None)
                env['WIEJSKAPAKA_DB'] = str(Path(tmp) / 'isolated.sqlite3')
                try:
                    p = subprocess.run([sys.executable, '-m', 'pytest', '-q', file], cwd=ROOT, env=env, text=True, capture_output=True, timeout=65)
                    row = {'file': file, 'status': 'PASS' if p.returncode == 0 else 'FAIL', 'returncode': p.returncode, 'tail': (p.stdout + '\n' + p.stderr)[-1300:]}
                except subprocess.TimeoutExpired:
                    row = {'file': file, 'status': 'TIMEOUT', 'tail': '65s timeout'}
        row = {**row, 'fingerprint': fingerprint(file), 'reused_from_checkpoint': file in done}
        report['results'].append(row)
        report['passed'] = sum(r['status'] == 'PASS' for r in report['results'])
        report['failed'] = sum(r['status'] != 'PASS' for r in report['results'])
        report['complete'] = len(report['results']) == len(FILES)
        REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n')
        print(f"{len(report['results'])}/{len(FILES)} {row['status']} {file}", flush=True)
    return 0 if report['complete'] and not report['failed'] else 1

if __name__ == '__main__':
    sys.exit(main())

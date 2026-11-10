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
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.run_tests_isolated import test_environment
from scripts.aggregate_full_regression import write_report_atomic
from scripts.regression_manifest import application_fingerprint
REPORT = ROOT / 'RAPORT_B_9841_10200_BEZPIECZENSTWO_IZOLACJA.json'
FINGERPRINT_PATHS = sorted(
    path for folder in ('backend', 'scripts', 'web', 'database')
    for path in (ROOT / folder).rglob('*')
    if path.is_file() and path.suffix in ('.py', '.js', '.html', '.css', '.sql')
) + [ROOT / 'tests' / 'conftest.py', ROOT / 'requirements.txt', ROOT / 'requirements-lock.txt']

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
    initial = {file: fingerprint(file) for file in FILES}
    initial_application = application_fingerprint(ROOT)
    prior = json.loads(REPORT.read_text(encoding='utf-8')) if REPORT.exists() else {}
    prior_results = prior.get('results', []) if prior.get('application_sha256') == initial_application else []
    done = {r['file']: r for r in prior_results if r.get('file') in initial and r.get('status') == 'PASS' and r.get('fingerprint') == initial[r['file']]}
    report = {'generated_utc': datetime.now(timezone.utc).isoformat(), 'scope': 'focused security and financial regression, per-module isolated SQLite', 'modules_total': len(FILES), 'application_sha256': initial_application, 'complete': False, 'success': False, 'results': []}
    write_report_atomic(REPORT, report)
    for file in FILES:
        if file in done:
            row = done[file]
        else:
            with tempfile.TemporaryDirectory(prefix='wp_security_') as tmp:
                env = test_environment(os.environ, Path(tmp) / 'isolated.sqlite3')
                try:
                    p = subprocess.run([sys.executable, '-m', 'pytest', '-q', file], cwd=ROOT, env=env, text=True, encoding='utf-8', capture_output=True, timeout=65)
                    row = {'file': file, 'status': 'PASS' if p.returncode == 0 else 'FAIL', 'returncode': p.returncode, 'tail': (p.stdout + '\n' + p.stderr)[-1300:]}
                except (subprocess.TimeoutExpired, OSError) as exc:
                    row = {'file': file, 'status': 'FAIL', 'error': type(exc).__name__}
        row = {**row, 'fingerprint': initial[file], 'reused_from_checkpoint': file in done}
        if fingerprint(file) != initial[file]:
            row.update(status='STALE', error='sources_changed_during_run')
        report['results'].append(row)
        report['passed'] = sum(r['status'] == 'PASS' for r in report['results'])
        report['failed'] = sum(r['status'] != 'PASS' for r in report['results'])
        write_report_atomic(REPORT, report)
        print(f"{len(report['results'])}/{len(FILES)} {row['status']} {file}", flush=True)
    report['sources_unchanged'] = application_fingerprint(ROOT) == initial_application and all(fingerprint(file) == initial[file] for file in FILES)
    report['complete'] = bool(FILES) and len(report['results']) == len(FILES) and report['sources_unchanged']
    report['success'] = report['complete'] and not report.get('failed', 0)
    write_report_atomic(REPORT, report)
    return 0 if report['success'] else 1

if __name__ == '__main__':
    sys.exit(main())

"""Audit unauthenticated requests against every non-public FastAPI route over loopback HTTP.

Disposable SQLite only. 401/403 = blocked; 404/422 = inconclusive (not a pass).
"""
import json
import os
import re
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.audit_route_auth_dependencies import audit, is_public
from scripts.run_phone_demo import demo_environment

PLACEHOLDERS = {'shipment_id': '9999999', 'order_id': '9999999', 'product_id': '9999999',
                'farmer_id': '9999999', 'notification_id': '9999999', 'draft_id': '9999999',
                'job_id': '9999999', 'request_key': 'not-existing', 'payout_date': '2026-10-15',
                'month': '2026-10'}

def resolved_path(path):
    return re.sub(r'\{([^}:]+)(?::[^}]+)?\}', lambda m: PLACEHOLDERS.get(m.group(1), '9999999'), path)

def run():
    with tempfile.TemporaryDirectory(prefix='wp_anon_audit_') as folder:
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            port = sock.getsockname()[1]
        env = demo_environment(os.environ, Path(folder) / 'isolated.sqlite3')
        proc = subprocess.Popen([sys.executable, '-m', 'uvicorn', 'backend.app:app', '--host', '127.0.0.1', '--port', str(port), '--no-access-log'], cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        results = []
        try:
            with httpx.Client(base_url=f'http://127.0.0.1:{port}', timeout=8, trust_env=False) as client:
                for _ in range(100):
                    if proc.poll() is not None:
                        raise RuntimeError(proc.communicate()[1].decode(errors='replace')[-1800:])
                    try:
                        if client.get('/health').status_code == 200:
                            break
                    except httpx.TransportError:
                        pass
                    time.sleep(.1)
                else:
                    raise TimeoutError('FastAPI did not start')
                for row in audit()['routes']:
                    method, path = row['method'], row['path']
                    if is_public(method, path):
                        continue
                    response = client.request(method, resolved_path(path), json={} if method in ('POST', 'PUT', 'PATCH') else None)
                    code = response.status_code
                    verdict = 'BLOCKED' if code in (401, 403) else ('INCONCLUSIVE' if code in (404, 405, 422) else 'REVIEW')
                    results.append({'method': method, 'path': path, 'status': code, 'verdict': verdict})
        finally:
            proc.terminate()
            try:
                proc.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.communicate(timeout=5)
    summary = {k: sum(r['verdict'] == k for r in results) for k in ('BLOCKED', 'INCONCLUSIVE', 'REVIEW')}
    return {'scope': 'Anonymous HTTP requests only; 404/422 are inconclusive, not authorization proofs', 'total': len(results), 'summary': summary, 'results': results}

if __name__ == '__main__':
    result = run()
    out = ROOT / 'RAPORT_ANONIMOWE_TRASY_HTTP_B_7321_7680.json'
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'total': result['total'], 'summary': result['summary'], 'review': [r for r in result['results'] if r['verdict'] != 'BLOCKED']}, ensure_ascii=False, indent=2))
    sys.exit(1 if result['summary']['REVIEW'] else 0)

"""B/8761: security headers and cache isolation on real local HTTP.

Uses a disposable SQLite database; does not access external services.
"""
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.run_phone_demo import demo_environment


def run():
    checks = []
    with tempfile.TemporaryDirectory(prefix='wp_headers_http_') as folder:
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            port = sock.getsockname()[1]
        env = demo_environment(os.environ, Path(folder) / 'test.sqlite3')
        proc = subprocess.Popen(
            [sys.executable, '-m', 'uvicorn', 'backend.app:app', '--host', '127.0.0.1', '--port', str(port), '--no-access-log'],
            cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
        )
        try:
            with httpx.Client(base_url=f'http://127.0.0.1:{port}', timeout=6, trust_env=False) as client:
                for _ in range(100):
                    if proc.poll() is not None:
                        raise RuntimeError('Backend exited: ' + proc.communicate()[1].decode(errors='replace')[-1200:])
                    try:
                        if client.get('/health').status_code == 200:
                            break
                    except httpx.TransportError:
                        pass
                    time.sleep(.1)
                else:
                    raise TimeoutError('HTTP startup')

                def verify(label, response, status, cache):
                    assert response.status_code == status, (label, response.status_code, response.text[:300])
                    h = response.headers
                    assert h.get('x-content-type-options') == 'nosniff', label
                    assert h.get('x-frame-options') == 'DENY', label
                    assert h.get('referrer-policy') == 'no-referrer', label
                    assert "object-src 'none'" in h.get('content-security-policy', ''), label
                    assert "frame-ancestors 'none'" in h.get('content-security-policy', ''), label
                    assert h.get('cache-control') == cache, (label, h.get('cache-control'))
                    if cache == 'no-store':
                        assert h.get('pragma') == 'no-cache', label
                    checks.append({'check': label, 'status': status, 'cache': cache})
                    return response

                verify('public home', client.get('/'), 200, 'no-cache')
                verify('public products', client.get('/products'), 200, 'no-cache')
                verify('public health', client.get('/health'), 200, 'no-cache')
                verify('anonymous private orders', client.get('/orders/me'), 401, 'no-store')
                verify('anonymous private identity', client.get('/auth/me'), 401, 'no-store')
                verify('invalid registration', client.post('/auth/register', json={}), 422, 'no-store')
                verify('nonexistent route', client.get('/not-a-route-8761'), 404, 'no-store')
                password = 'TestoweHaslo_123456789'
                email = 'headers-audit@example.invalid'
                verify('register', client.post('/auth/register', json={'email':email,'password':password,'role':'klient'}), 201, 'no-store')
                login = verify('login', client.post('/auth/login', json={'email':email,'password':password}), 200, 'no-store')
                headers = {'Authorization': 'Bearer ' + login.json()['access_token']}
                verify('authenticated identity', client.get('/auth/me', headers=headers), 200, 'no-store')
                verify('role restricted create product', client.post('/products', headers=headers, json={'name':'test','price_grosze':100,'delivery_grosze':0,'stock':1}), 403, 'no-store')
                verify('logout', client.post('/auth/logout', headers=headers), 200, 'no-store')
                verify('revoked session', client.get('/auth/me', headers=headers), 401, 'no-store')
        finally:
            proc.terminate()
            try:
                proc.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.communicate(timeout=5)
    return {'status': 'PASS', 'count': len(checks), 'checks': checks, 'scope': 'real local HTTP, disposable SQLite'}


if __name__ == '__main__':
    print(json.dumps(run(), ensure_ascii=False, indent=2))

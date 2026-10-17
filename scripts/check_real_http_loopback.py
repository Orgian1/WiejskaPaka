"""B/5701–5760: actual HTTP loopback smoke test with isolated disposable SQLite.

Never inherits Neon/PostgreSQL credentials. No production payment endpoints.
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
# Allow both `python -m scripts.<name>` and `python scripts/<name>.py`.
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def run():
    from scripts.run_phone_demo import demo_environment
    with tempfile.TemporaryDirectory(prefix='wiejskapaka_http_') as tmp:
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            port = sock.getsockname()[1]
        env = demo_environment(os.environ, Path(tmp) / 'http.sqlite3')
        command = [sys.executable, '-m', 'uvicorn', 'backend.app:app', '--host', '127.0.0.1', '--port', str(port), '--no-access-log']
        proc = subprocess.Popen(command, cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        results = []
        try:
            with httpx.Client(base_url=f'http://127.0.0.1:{port}', timeout=5, trust_env=False) as client:
                for _ in range(80):
                    if proc.poll() is not None:
                        raise RuntimeError(f'Serwer zakończył działanie: {proc.communicate()[1].decode(errors="replace")[-1200:]}')
                    try:
                        if client.get('/health').status_code == 200:
                            break
                    except httpx.TransportError:
                        pass
                    time.sleep(.15)
                else:
                    raise TimeoutError('Serwer HTTP nie uruchomił się w czasie 12 s')

                def check(name, response, status):
                    assert response.status_code == status, (name, response.status_code, response.text[:300])
                    assert response.headers.get('x-content-type-options') == 'nosniff', name
                    results.append({'test': name, 'status': 'PASS', 'http_status': status})
                    return response

                check('GET health', client.get('/health'), 200)
                check('GET catalog', client.get('/products'), 200)
                check('GET frontend', client.get('/'), 200)
                check('GET anonymous private orders', client.get('/orders/me'), 401)
                check('POST invalid register', client.post('/auth/register', json={}), 422)
                for role in ('klient', 'rolnik'):
                    email = f'http-{role}@example.invalid'
                    password = 'TestoweHaslo_123456789'
                    check(f'POST register {role}', client.post('/auth/register', json={'email':email,'password':password,'role':role}), 201)
                    login = check(f'POST login {role}', client.post('/auth/login', json={'email':email,'password':password}), 200)
                    headers = {'Authorization': 'Bearer ' + login.json()['access_token']}
                    check(f'GET identity {role}', client.get('/auth/me', headers=headers), 200)
                    check(f'POST logout {role}', client.post('/auth/logout', headers=headers), 200)
                    check(f'GET identity after logout {role}', client.get('/auth/me', headers=headers), 401)
                assert client.get('/products').headers['cache-control'] == 'no-cache'
                assert client.get('/orders/me').headers['cache-control'] == 'no-store'
                results.append({'test':'HTTP cache-control separation', 'status':'PASS'})
        finally:
            proc.terminate()
            try:
                proc.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.communicate(timeout=5)
        return {'scope':'actual HTTP over 127.0.0.1 with disposable SQLite; no PostgreSQL or external services', 'passed':len(results), 'results':results}


if __name__ == '__main__':
    report = run()
    print(json.dumps(report, ensure_ascii=False, indent=2))

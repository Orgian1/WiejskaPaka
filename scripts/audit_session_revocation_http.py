"""Real HTTP test of independent sessions, logout and logout-all; disposable local SQLite."""
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
sys.path.insert(0, str(ROOT))
from scripts.run_phone_demo import demo_environment


def run():
    checks = []
    with tempfile.TemporaryDirectory(prefix='wp_sessions_http_') as folder:
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            port = sock.getsockname()[1]
        env = demo_environment(os.environ, Path(folder) / 'sessions.sqlite3')
        proc = subprocess.Popen([sys.executable, '-m', 'uvicorn', 'backend.app:app', '--host', '127.0.0.1', '--port', str(port), '--no-access-log'], cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        try:
            with httpx.Client(base_url=f'http://127.0.0.1:{port}', timeout=8, trust_env=False) as client:
                for _ in range(100):
                    if proc.poll() is not None:
                        raise RuntimeError(proc.communicate()[1].decode(errors='replace')[-1500:])
                    try:
                        if client.get('/health').status_code == 200:
                            break
                    except httpx.TransportError:
                        pass
                    time.sleep(.1)
                else:
                    raise TimeoutError('Local HTTP startup failed')

                def verify(label, method, path, status, token=None, payload=None, authorization=None):
                    headers = {}
                    if token is not None:
                        headers['Authorization'] = 'Bearer ' + token
                    if authorization is not None:
                        headers['Authorization'] = authorization
                    response = client.request(method, path, headers=headers, json=payload)
                    assert response.status_code == status, (label, response.status_code, response.text[:350])
                    checks.append(label)
                    return response.json()

                users = {}
                for name, role in [('buyer', 'klient'), ('farmer', 'rolnik')]:
                    email = f'session-audit-{name}@example.invalid'
                    credentials = {'email': email, 'password': 'TestoweHaslo_123456789'}
                    verify(f'register {name}', 'POST', '/auth/register', 201, payload={**credentials, 'role': role})
                    tokens = [verify(f'login {name} session {n}', 'POST', '/auth/login', 200, payload=credentials)['access_token'] for n in range(1, 4)]
                    assert len(set(tokens)) == 3
                    checks.append(f'unique independent tokens {name}')
                    users[name] = (credentials, tokens)
                buyer = users['buyer'][1]
                farmer = users['farmer'][1]
                for token in buyer + farmer:
                    verify('valid token accesses profile', 'GET', '/auth/me', 200, token=token)
                for label, header in [('missing', None), ('wrong scheme', 'Basic test'), ('empty bearer', 'Bearer'), ('forged', 'Bearer invalid-token')]:
                    verify(f'reject {label}', 'GET', '/auth/me', 401, authorization=header)
                verify('logout one buyer session', 'POST', '/auth/logout', 200, token=buyer[0])
                verify('revoked buyer token rejected', 'GET', '/auth/me', 401, token=buyer[0])
                for token in buyer[1:] + farmer:
                    verify('other session remains valid after single logout', 'GET', '/auth/me', 200, token=token)
                verify('repeated logout of revoked token rejected', 'POST', '/auth/logout', 401, token=buyer[0])
                verify('logout all buyer sessions', 'POST', '/auth/logout-all', 200, token=buyer[1])
                for token in buyer:
                    verify('buyer token invalid after logout all', 'GET', '/auth/me', 401, token=token)
                for token in farmer:
                    verify('farmer token survives buyer logout all', 'GET', '/auth/me', 200, token=token)
                verify('farmer logout all', 'POST', '/auth/logout-all', 200, token=farmer[2])
                for token in farmer:
                    verify('farmer token revoked', 'GET', '/auth/me', 401, token=token)
                fresh = verify('login again after logout all', 'POST', '/auth/login', 200, payload=users['buyer'][0])['access_token']
                verify('fresh token works', 'GET', '/auth/me', 200, token=fresh)
        finally:
            proc.terminate()
            try:
                proc.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.communicate(timeout=5)
    return {'status': 'PASS', 'passed': len(checks), 'checks': checks, 'scope': 'Real HTTP loopback; isolated disposable SQLite; no Neon or real payments'}


if __name__ == '__main__':
    print(json.dumps(run(), ensure_ascii=False, indent=2))

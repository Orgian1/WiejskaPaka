"""B/10921: real loopback HTTP login throttling and account isolation audit."""
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
    with tempfile.TemporaryDirectory(prefix='wp_lockout_b10921_') as directory:
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            port = sock.getsockname()[1]
        env = demo_environment(os.environ, Path(directory) / 'lockout.sqlite3')
        process = subprocess.Popen([sys.executable, '-m', 'uvicorn', 'backend.app:app', '--host', '127.0.0.1', '--port', str(port), '--no-access-log'], cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        try:
            with httpx.Client(base_url=f'http://127.0.0.1:{port}', timeout=10, trust_env=False) as client:
                for _ in range(100):
                    if process.poll() is not None:
                        raise RuntimeError(process.communicate()[1].decode(errors='replace')[-1500:])
                    try:
                        if client.get('/health').status_code == 200:
                            break
                    except httpx.TransportError:
                        pass
                    time.sleep(.1)
                else:
                    raise TimeoutError('HTTP startup timeout')

                def check(label, method, endpoint, expected, **kwargs):
                    response = client.request(method, endpoint, **kwargs)
                    assert response.status_code == expected, (label, response.status_code, response.text[:300])
                    checks.append(label)
                    return response

                good = 'StrongPass_123456789'
                a = {'email': 'lockout-a@example.invalid', 'password': good}
                b = {'email': 'lockout-b@example.invalid', 'password': good}
                for who, credentials in [('A', a), ('B', b)]:
                    check('register ' + who, 'POST', '/auth/register', 201, json={**credentials, 'role': 'klient'})
                bad = {**a, 'password': 'Incorrect_123456789'}
                for index in range(1, 6):
                    check(f'bad password attempt {index}', 'POST', '/auth/login', 401, json=bad)
                check('locked correct password', 'POST', '/auth/login', 429, json=a)
                check('locked wrong password', 'POST', '/auth/login', 429, json=bad)
                check('independent account login', 'POST', '/auth/login', 200, json=b)
                check('unknown account rejected', 'POST', '/auth/login', 401, json={'email': 'unknown@example.invalid', 'password': good})
                check('locked account remains locked', 'POST', '/auth/login', 429, json=a)
                check('email normalization still works', 'POST', '/auth/login', 200, json={**b, 'email': '  LOCKOUT-B@EXAMPLE.INVALID  '})
        finally:
            process.terminate()
            try:
                process.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.communicate(timeout=5)
    return {'status': 'PASS', 'passed': len(checks), 'checks': checks, 'environment': 'loopback HTTP + disposable SQLite', 'postgresql_tested': False, 'physical_mobile_tested': False}


if __name__ == '__main__':
    print(json.dumps(run(), ensure_ascii=False, indent=2))

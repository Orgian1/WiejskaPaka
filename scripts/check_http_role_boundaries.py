"""Live loopback HTTP authorization matrix, disposable SQLite only."""
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
    with tempfile.TemporaryDirectory(prefix='wp_role_http_') as folder:
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            port = sock.getsockname()[1]
        env = demo_environment(os.environ, Path(folder) / 'isolated.sqlite3')
        proc = subprocess.Popen([sys.executable, '-m', 'uvicorn', 'backend.app:app', '--host', '127.0.0.1', '--port', str(port), '--no-access-log'], cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        checks = []
        try:
            with httpx.Client(base_url=f'http://127.0.0.1:{port}', timeout=5, trust_env=False) as client:
                for _ in range(80):
                    if proc.poll() is not None:
                        raise RuntimeError(proc.communicate()[1].decode(errors='replace')[-1500:])
                    try:
                        if client.get('/health').status_code == 200:
                            break
                    except httpx.TransportError:
                        pass
                    time.sleep(.15)
                else:
                    raise TimeoutError('FastAPI did not start')

                def check(label, method, path, expected, headers=None, json_body=None):
                    response = client.request(method, path, headers=headers, json=json_body)
                    assert response.status_code == expected, (label, response.status_code, response.text[:250])
                    assert response.headers.get('x-content-type-options') == 'nosniff', label
                    checks.append(label)
                    return response

                protected = [
                    ('GET', '/orders/me', None),
                    ('GET', '/shipments/mine', None),
                    ('GET', '/shipments/farmer/mine', None),
                    ('GET', '/couriers/me/active-addresses', None),
                    ('GET', '/admin/shipments/overview', None),
                    ('GET', '/test/farmers/me/payout-report', None),
                    ('GET', '/notifications/me', None),
                    ('POST', '/products', {'name':'Marchew','price_grosze':349,'delivery_grosze':501,'stock':3}),
                ]
                for method, path, body in protected:
                    check(f'anonymous {method} {path}', method, path, 401, json_body=body)
                headers_by_role = {}
                for role in ('klient', 'rolnik', 'dostawca'):
                    email = f'http-boundary-{role}@example.invalid'
                    password = 'TestoweHaslo_123456789'
                    check(f'register {role}', 'POST', '/auth/register', 201, json_body={'email':email,'password':password,'role':role})
                    response = check(f'login {role}', 'POST', '/auth/login', 200, json_body={'email':email,'password':password})
                    headers_by_role[role] = {'Authorization':'Bearer '+response.json()['access_token']}
                for role, headers in headers_by_role.items():
                    for path in ('/admin/shipments/overview', '/admin/shipments/reconciliation'):
                        check(f'{role} denied {path}', 'GET', path, 403, headers)
                    if role != 'dostawca':
                        check(f'{role} denied courier addresses', 'GET', '/couriers/me/active-addresses', 403, headers)
                    if role != 'rolnik':
                        check(f'{role} payout simulation disabled for', 'GET', '/test/farmers/me/payout-report', 404, headers)
                        check(f'{role} denied product create', 'POST', '/products', 403, headers, {'name':'Marchew','price_grosze':349,'delivery_grosze':501,'stock':3})
                check('farmer creates product', 'POST', '/products', 201, headers_by_role['rolnik'], {'name':'Marchew','price_grosze':349,'delivery_grosze':501,'stock':3})
                products = check('public catalog', 'GET', '/products', 200).json()
                assert len(products) == 1 and products[0]['price_grosze'] == 349
                assert all('phone' not in k.lower() and 'telefon' not in k.lower() for k in products[0])
                checks.append('public catalog price in grosze without phone numbers')
                for role, headers in headers_by_role.items():
                    check(f'logout {role}', 'POST', '/auth/logout', 200, headers)
                    check(f'revoked token {role}', 'GET', '/auth/me', 401, headers)
        finally:
            proc.terminate()
            try:
                proc.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.communicate(timeout=5)
        return {'status':'PASS','passed':len(checks),'checks':checks,'scope':'real HTTP loopback, disposable SQLite, no external connections'}


if __name__ == '__main__':
    print(json.dumps(run(), ensure_ascii=False, indent=2))

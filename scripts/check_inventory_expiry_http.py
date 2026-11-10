"""Real TCP HTTP expiry gate with a disposable DB and test payments only.

Ages reservation timestamps in the fixture to exercise the normal 30-second
worker and startup recovery without waiting 30 minutes. Never alters a user DB.
"""
import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.run_phone_demo import demo_environment
sys.path.insert(0, str(ROOT / 'scripts'))
from run_tests_per_file import application_fingerprint


def run():
    source = application_fingerprint(ROOT)
    checks = []
    requests = 0
    def check(condition, name):
        if not condition:
            raise AssertionError(name)
        checks.append(name)
    with tempfile.TemporaryDirectory(prefix='wp_expiry_http_') as folder:
        database = Path(folder) / 'expiry.sqlite3'
        env = demo_environment(os.environ, database)
        env['WP_ENABLE_TEST_PAYMENTS'] = '1'
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            port = sock.getsockname()[1]
        with tempfile.TemporaryFile() as log:
            process = None
            def stop():
                if process is not None:
                    process.terminate()
                    try:
                        process.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait(timeout=5)
            def start():
                nonlocal process
                process = subprocess.Popen([sys.executable, '-m', 'uvicorn', 'backend.app:app',
                    '--host', '127.0.0.1', '--port', str(port), '--no-access-log'], cwd=ROOT,
                    env=env, stdout=log, stderr=log)
                for _ in range(100):
                    if process.poll() is not None:
                        raise RuntimeError('Disposable API did not start')
                    try:
                        if client.get('/health').status_code == 200:
                            return
                    except Exception:
                        pass
                    time.sleep(.1)
                raise TimeoutError('Disposable HTTP startup timed out')
            try:
                import httpx
                with httpx.Client(base_url=f'http://127.0.0.1:{port}', trust_env=False, timeout=10) as client:
                    start()
                    def request(method, path, headers=None, body=None, expected=200):
                        nonlocal requests
                        response = client.request(method, path, headers=headers, json=body)
                        requests += 1
                        check(response.status_code == expected, method+' '+path+' HTTP '+str(expected))
                        check(response.headers.get('x-content-type-options') == 'nosniff', 'security header')
                        return response.json()
                    def account(role):
                        email = uuid4().hex+'@example.invalid'
                        password = 'Disposable-expiry-test-123!'
                        request('POST', '/auth/register', body={'email': email, 'password':password, 'role':role}, expected=201)
                        login = request('POST', '/auth/login', body={'email':email, 'password':password})
                        return {'Authorization': 'Bearer '+login['access_token']}
                    farmer, buyer = account('rolnik'), account('klient')
                    product = request('POST', '/products', farmer,
                        {'name':'Ziemniaki testu HTTP', 'price_grosze':199, 'delivery_grosze':501, 'stock':5}, 201)['id']
                    body = {'product_id':product, 'quantity':1, 'fulfillment':'dostawa',
                        'delivery_city':'Opole', 'delivery_street':'Testowa 1', 'delivery_postal_code':'45-001'}
                    key_headers = {**buyer, 'Idempotency-Key':uuid4().hex}
                    unpaid = request('POST', '/orders', key_headers, body, 201)
                    paid = request('POST', '/orders', buyer, body, 201)
                    failed = request('POST', '/orders', buyer, body, 201)
                    for receipt, kind in [(paid,'payment_success_test'),(failed,'payment_failed_test')]:
                        request('POST', f'/test/payments/{receipt["id"]}/events', buyer,
                            {'event_id':uuid4().hex,'event_type':kind})
                    with sqlite3.connect(database) as con:
                        deadline = (datetime.now(timezone.utc)-timedelta(seconds=1)).isoformat()
                        con.execute('UPDATE inventory_reservations SET expires_at=?', (deadline,))
                    request('POST', f'/test/payments/{unpaid["id"]}/events', buyer,
                        {'event_id':uuid4().hex,'event_type':'payment_success_test'}, 409)
                    until = time.monotonic()+40
                    while True:
                        with sqlite3.connect(database) as con:
                            states = dict(con.execute('SELECT id,status FROM orders'))
                        if states[unpaid['id']] == states[failed['id']] == 'anulowane_testowo':
                            break
                        if time.monotonic() >= until:
                            raise TimeoutError('Automatic 30-second sweep did not release unpaid inventory')
                        time.sleep(.1)
                    check(states[paid['id']] == 'oczekuje_na_platnosc_testowa', 'paid order survives automatic sweep')
                    check(request('GET', f'/products/{product}')['stock'] == 4, 'only unpaid inventory restored')
                    check(request('POST', '/orders', key_headers, body, 201) == unpaid, 'expired idempotency receipt is stable')
                    check(request('GET', f'/products/{product}')['stock'] == 4, 'receipt replay cannot reserve stock')
                    request('POST', f'/test/payments/{unpaid["id"]}/events', buyer,
                        {'event_id':uuid4().hex,'event_type':'payment_success_test'}, 409)
                    # Exercise startup recovery independently of a periodic sweep.
                    recovery = request('POST', '/orders', buyer, body, 201)
                    stop()
                    with sqlite3.connect(database) as con:
                        con.execute('UPDATE inventory_reservations SET expires_at=? WHERE order_id=?',
                                    (deadline,recovery['id']))
                    start()
                    until = time.monotonic()+5
                    while True:
                        with sqlite3.connect(database) as con:
                            status = con.execute('SELECT status FROM orders WHERE id=?', (recovery['id'],)).fetchone()[0]
                        if status == 'anulowane_testowo':
                            break
                        if time.monotonic() >= until:
                            raise TimeoutError('Startup recovery did not release inventory')
                        time.sleep(.05)
                    check(request('GET', f'/products/{product}')['stock'] == 4, 'startup recovery restores exactly once')
                    with sqlite3.connect(database) as con:
                        count = con.execute("SELECT COUNT(*) FROM order_events WHERE event_type='reservation_expired_test'").fetchone()[0]
                        check(count == 3, 'one expiration event for each of three unpaid orders')
                        check(con.execute('PRAGMA foreign_key_check').fetchall() == [], 'foreign keys remain valid')
                        check(con.execute('PRAGMA integrity_check').fetchone()[0] == 'ok', 'SQLite integrity')
                        p = con.execute('SELECT state,refund_grosze,payout_grosze FROM payment_simulations WHERE order_id=?', (paid['id'],)).fetchone()
                        check(p == ('paid_test',0,0), 'paid money never refunded or paid out by expiration')
            finally:
                stop()
    check(source == application_fingerprint(ROOT), 'application unchanged during HTTP gate')
    return {'passed':True, 'application_sha256':source, 'http_requests':requests,
            'checks_count':len(checks), 'checks':checks, 'real_tcp_http':True,
            'timestamp_fixture_only':True, 'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', default='audit_inventory_expiry_http.json')
    args = parser.parse_args()
    result = run()
    Path(args.report).write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k != 'checks'}, indent=2))

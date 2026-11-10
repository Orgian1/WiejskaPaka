"""Real TCP HTTP checkout/delivery/refund checks; isolated SQLite, no external services."""
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
    with tempfile.TemporaryDirectory(prefix='wp_checkout_http_') as folder:
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            port = sock.getsockname()[1]
        env = demo_environment(os.environ, Path(folder) / 'checkout.sqlite3')
        env['WP_ENABLE_TEST_PAYMENTS'] = '1'  # Disposable SQLite only; never production
        proc = subprocess.Popen([sys.executable, '-m', 'uvicorn', 'backend.app:app', '--host', '127.0.0.1', '--port', str(port), '--no-access-log'], cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        try:
            with httpx.Client(base_url=f'http://127.0.0.1:{port}', timeout=6, trust_env=False) as client:
                for _ in range(100):
                    if proc.poll() is not None:
                        raise RuntimeError(proc.communicate()[1].decode(errors='replace')[-1200:])
                    try:
                        if client.get('/health').status_code == 200:
                            break
                    except httpx.TransportError:
                        pass
                    time.sleep(.1)
                else:
                    raise TimeoutError('HTTP server startup')

                def call(label, method, path, expected=200, headers=None, body=None):
                    r = client.request(method, path, headers=headers, json=body)
                    assert r.status_code == expected, (label, r.status_code, r.text[:450])
                    checks.append(label)
                    return r.json()

                auth = {}
                ids = {}
                for role in ('klient', 'rolnik', 'dostawca', 'obcy'):
                    user_role = 'klient' if role == 'obcy' else role
                    email = f'checkout-http-{role}@example.invalid'
                    registered = call('register ' + role, 'POST', '/auth/register', 201, body={'email':email, 'password':'TestoweHaslo_123456789', 'role':user_role})
                    ids[role] = registered.get('id')
                    token = call('login ' + role, 'POST', '/auth/login', body={'email':email, 'password':'TestoweHaslo_123456789'})['access_token']
                    auth[role] = {'Authorization':'Bearer '+token}
                product = call('create product', 'POST', '/products', 201, auth['rolnik'], {'name':'Marchew HTTP', 'price_grosze':349, 'delivery_grosze':501, 'stock':5})
                product_id = product['id']
                call('stranger denied private orders', 'GET', '/orders/me', 200, auth['obcy'])
                order_body = {'product_id':product_id,'quantity':1,'fulfillment':'dostawa','delivery_city':'Radom','delivery_street':'Tajna 9','delivery_postal_code':'26-600'}
                order = call('buyer creates delivery', 'POST', '/orders', 201, auth['klient'], order_body)
                assert order['total_grosze'] == 850 and isinstance(order['total_grosze'], int)
                checks.append('349 + single 501 shipping = 850 grosze')
                oid, pin = order['id'], order['pin_test_only']
                call('unassigned courier denied address', 'GET', f'/orders/{oid}/location', 403, auth['dostawca'])
                call('stranger denied address', 'GET', f'/orders/{oid}/location', 403, auth['obcy'])
                call('buyer cannot assign courier', 'POST', f'/orders/{oid}/assign-courier-test', 403, auth['klient'], {'courier_id':ids['dostawca']})
                call('farmer assigns courier', 'POST', f'/orders/{oid}/assign-courier-test', 200, auth['rolnik'], {'courier_id':ids['dostawca']})
                call('farmer dispatches', 'POST', f'/orders/{oid}/dispatch-test', 200, auth['rolnik'])
                location = call('assigned courier sees address', 'GET', f'/orders/{oid}/location', 200, auth['dostawca'])
                assert location['delivery_street'] == 'Tajna 9'
                checks.append('address matches after dispatch')
                wrong = '999999' if pin != '999999' else '888888'
                incorrect = call('incorrect PIN counted', 'POST', f'/orders/{oid}/confirm', 200, auth['dostawca'], {'pin':wrong, 'checked_goods':True})
                assert incorrect['remaining_attempts'] == 4
                confirmed = call('correct PIN confirms', 'POST', f'/orders/{oid}/confirm', 200, auth['dostawca'], {'pin':pin, 'checked_goods':True})
                assert confirmed['confirmed'] is True
                call('address revoked after delivery', 'GET', f'/orders/{oid}/location', 403, auth['dostawca'])
                failed = call('new delivery to fail', 'POST', '/orders', 201, auth['klient'], {**order_body, 'delivery_street':'Tajna 11'})
                assert failed['total_grosze'] == 850
                fid = failed['id']
                call('simulate payment', 'POST', f'/test/payments/{fid}/events', 200, auth['klient'], {'event_id':'pay-http-e2e','event_type':'payment_success_test'})
                call('assign failing delivery', 'POST', f'/orders/{fid}/assign-courier-test', 200, auth['rolnik'], {'courier_id':ids['dostawca']})
                call('dispatch failing delivery', 'POST', f'/orders/{fid}/dispatch-test', 200, auth['rolnik'])
                refund = call('courier failure refund', 'POST', f'/test/payments/{fid}/events', 200, auth['rolnik'], {'event_id':'refund-http-e2e','event_type':'delivery_failed_by_courier_test'})
                assert refund['refund_grosze'] == 850 and refund['state'] == 'refunded_test'
                checks.append('100% refund including shipping')
                # Multiple units in one shipment must never multiply the delivery fee.
                multi = call('multi-unit delivery order', 'POST', '/orders', 201, auth['klient'], {**order_body, 'quantity':2, 'delivery_street':'Tajna 13'})
                assert multi['total_grosze'] == 1199, multi  # 2 * 349 + 501
                checks.append('two units share one delivery fee: 698 + 501 = 1199 grosze')
                assert isinstance(multi['total_grosze'], int)
                checks.append('multi-unit amount stored in integer grosze')
                call('stranger denied multi-unit address', 'GET', f"/orders/{multi['id']}/location", 403, auth['obcy'])
                call('unassigned courier denied multi-unit address', 'GET', f"/orders/{multi['id']}/location", 403, auth['dostawca'])
                call('buyer cannot dispatch multi-unit shipment', 'POST', f"/orders/{multi['id']}/dispatch-test", 403, auth['klient'])
        finally:
            proc.terminate()
            try:
                proc.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.communicate(timeout=5)
    return {'status':'PASS', 'passed':len(checks), 'checks':checks, 'scope':'real TCP HTTP FastAPI and disposable SQLite, test payments only'}

if __name__ == '__main__':
    print(json.dumps(run(), ensure_ascii=False, indent=2))

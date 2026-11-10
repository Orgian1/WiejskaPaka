"""Actual loopback HTTP multi-seller cart test, disposable SQLite and no external payments."""
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
    with tempfile.TemporaryDirectory(prefix='wp_multi_seller_http_') as tmp:
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            port = sock.getsockname()[1]
        env = demo_environment(os.environ, Path(tmp) / 'cart.sqlite3')
        env['WP_ENABLE_TEST_PAYMENTS'] = '1'
        proc = subprocess.Popen([sys.executable, '-m', 'uvicorn', 'backend.app:app', '--host', '127.0.0.1', '--port', str(port), '--no-access-log'], cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        try:
            with httpx.Client(base_url=f'http://127.0.0.1:{port}', timeout=8, trust_env=False) as c:
                for _ in range(100):
                    if proc.poll() is not None:
                        raise RuntimeError(proc.communicate()[1].decode(errors='replace')[-1500:])
                    try:
                        if c.get('/health').status_code == 200:
                            break
                    except httpx.TransportError:
                        pass
                    time.sleep(.1)
                else:
                    raise TimeoutError('HTTP startup')

                def req(label, method, path, status=200, headers=None, body=None):
                    r = c.request(method, path, headers=headers, json=body)
                    assert r.status_code == status, (label, r.status_code, r.text[:500])
                    checks.append(label)
                    return r.json()

                auth, ids = {}, {}
                for role in ('klient', 'rolnik_a', 'rolnik_b', 'obcy'):
                    kind = 'rolnik' if role.startswith('rolnik') else 'klient'
                    email = f'multicart-{role}@example.invalid'
                    ids[role] = req('register '+role, 'POST', '/auth/register', 201, body={'email': email, 'password':'TestoweHaslo_123456789', 'role':kind})['id']
                    token = req('login '+role, 'POST', '/auth/login', body={'email':email,'password':'TestoweHaslo_123456789'})['access_token']
                    auth[role] = {'Authorization':'Bearer '+token}
                specs = [('rolnik_a', 'Jablka', 349, 501, 20), ('rolnik_a', 'Gruszki', 257, 699, 20), ('rolnik_b', 'Miod', 999, 801, 20)]
                products = []
                for role, name, price, fee, stock in specs:
                    products.append(req('product '+name, 'POST', '/products', 201, auth[role], {'name':name, 'price_grosze':price, 'delivery_grosze':fee, 'stock':stock})['id'])
                for product_id, quantity in zip(products, (2, 3, 1)):
                    req('save cart '+str(product_id), 'PUT', '/cart/items', 200, auth['klient'], {'product_id':product_id,'quantity':quantity})
                quote = req('quote two sellers', 'POST', '/cart/quote', 200, auth['klient'], {'items':[{'product_id':p,'quantity':q} for p,q in zip(products,(2,3,1))], 'fulfillment':'dostawa'})
                pickup_quote = req('pickup quote for both sellers', 'POST', '/cart/quote', 200, auth['klient'], {'items':[{'product_id':p,'quantity':q} for p,q in zip(products,(2,3,1))], 'fulfillment':'odbior'})
                assert pickup_quote['subtotal_grosze'] == 2468 and pickup_quote['delivery_grosze'] == 0 and pickup_quote['total_grosze'] == 2468
                assert len(pickup_quote['shipments']) == 2 and all(s['delivery_grosze'] == 0 for s in pickup_quote['shipments'])
                checks.append('pickup for two sellers has zero delivery charge')
                req('duplicate product in quote rejected', 'POST', '/cart/quote', 422, auth['klient'], {'items':[{'product_id':products[0],'quantity':1},{'product_id':products[0],'quantity':1}], 'fulfillment':'dostawa'})
                req('insufficient stock rejected', 'POST', '/cart/quote', 409, auth['klient'], {'items':[{'product_id':products[0],'quantity':21}], 'fulfillment':'dostawa'})
                req('stranger cannot quote buyer cart', 'POST', '/cart/quote', 200, auth['obcy'], {'items':[{'product_id':products[0],'quantity':1}], 'fulfillment':'dostawa'})
                req('farmer cannot use buyer quote', 'POST', '/cart/quote', 403, auth['rolnik_a'], {'items':[{'product_id':products[0],'quantity':1}], 'fulfillment':'dostawa'})
                # Seller A: 698+771+max(501,699)=2168; Seller B: 999+801=1800.
                assert (quote['subtotal_grosze'], quote['delivery_grosze'], quote['total_grosze']) == (2468,1500,3968), quote
                assert len(quote['shipments']) == 2
                checks.append('two sellers: one maximum delivery charge per seller')
                body = {'fulfillment':'dostawa','delivery_city':'Radom','delivery_street':'Tajna 20','delivery_postal_code':'26-600'}
                req('checkout without farmer selection rejected', 'POST', '/cart/checkout-test', 422, auth['klient'], body)
                first = req('checkout seller A', 'POST', '/cart/checkout-test', 201, {**auth['klient'], 'Idempotency-Key':'multi-seller-checkout-a-0001'}, {**body,'farmer_id':ids['rolnik_a']})
                assert first['total_grosze'] == 2168 and first['delivery_grosze'] == 699 and len(first['orders']) == 2, first
                checks.append('seller A two different products, one 699 grosze shipping')
                replay = req('idempotent replay seller A', 'POST', '/cart/checkout-test', 201, {**auth['klient'], 'Idempotency-Key':'multi-seller-checkout-a-0001'}, {**body,'farmer_id':ids['rolnik_a']})
                assert replay == first
                checks.append('idempotency prevents duplicate shipment')
                req('reused key different payload rejected', 'POST', '/cart/checkout-test', 409, {**auth['klient'], 'Idempotency-Key':'multi-seller-checkout-a-0001'}, {**body,'farmer_id':ids['rolnik_b']})
                remaining = req('remaining cart', 'GET', '/cart/items', 200, auth['klient'])
                assert str(products[2]) in json.dumps(remaining), remaining
                checks.append('seller B products retained after seller A checkout')
                second = req('checkout seller B', 'POST', '/cart/checkout-test', 201, auth['klient'], {**body,'farmer_id':ids['rolnik_b']})
                assert second['total_grosze'] == 1800 and second['delivery_grosze'] == 801 and len(second['orders']) == 1, second
                assert first['total_grosze'] + second['total_grosze'] == quote['total_grosze']
                checks.append('sum of two separate shipments matches basket quote')
                req('stranger denied seller A shipment details', 'GET', f"/shipments/{first['shipment_id']}/details", 404, auth['obcy'])
                req('seller B denied seller A shipment details', 'GET', f"/shipments/{first['shipment_id']}/details", 404, auth['rolnik_b'])
                details = req('buyer sees own shipment', 'GET', f"/shipments/{first['shipment_id']}/details", 200, auth['klient'])
                assert details['delivery_grosze'] == 699
                checks.append('shipment details retain single shipping fee')

                # Cross-account shipment IDOR: buyer, each seller and unrelated buyer.
                req('anonymous cannot read shipment details', 'GET', f"/shipments/{first['shipment_id']}/details", 401)
                req('seller A can read own shipment', 'GET', f"/shipments/{first['shipment_id']}/details", 200, auth['rolnik_a'])
                req('seller A denied seller B shipment', 'GET', f"/shipments/{second['shipment_id']}/details", 404, auth['rolnik_a'])
                req('seller B can read own shipment', 'GET', f"/shipments/{second['shipment_id']}/details", 200, auth['rolnik_b'])
                req('stranger denied seller B shipment', 'GET', f"/shipments/{second['shipment_id']}/details", 404, auth['obcy'])
                req('stranger denied seller A financial history', 'GET', f"/shipments/{first['shipment_id']}/financial-history-test", 404, auth['obcy'])
                req('seller A denied buyer financial history', 'GET', f"/shipments/{first['shipment_id']}/financial-history-test", 403, auth['rolnik_a'])
                req('seller B denied buyer financial history', 'GET', f"/shipments/{second['shipment_id']}/financial-history-test", 403, auth['rolnik_b'])
                req('buyer can read own financial history', 'GET', f"/shipments/{first['shipment_id']}/financial-history-test", 200, auth['klient'])
                buyer_shipments = req('buyer sees both shipments', 'GET', '/shipments/mine', 200, auth['klient'])
                own_ids = {row['id'] for row in buyer_shipments['shipments']}
                assert {first['shipment_id'], second['shipment_id']} <= own_ids
                checks.append('buyer shipment list contains both sellers')
                stranger_shipments = req('stranger sees own empty shipments', 'GET', '/shipments/mine', 200, auth['obcy'])
                assert not stranger_shipments['shipments']
                checks.append('stranger shipment list is empty')
                seller_a_shipments = req('seller A sees own shipments', 'GET', '/shipments/farmer/mine', 200, auth['rolnik_a'])
                assert {row['id'] for row in seller_a_shipments['shipments']} == {first['shipment_id']}
                checks.append('seller A shipment list excludes seller B')
                seller_b_shipments = req('seller B sees own shipments', 'GET', '/shipments/farmer/mine', 200, auth['rolnik_b'])
                assert {row['id'] for row in seller_b_shipments['shipments']} == {second['shipment_id']}
                checks.append('seller B shipment list excludes seller A')
                req('buyer denied farmer shipment listing', 'GET', '/shipments/farmer/mine', 403, auth['klient'])
                req('farmer denied buyer shipment listing', 'GET', '/shipments/mine', 403, auth['rolnik_a'])

        finally:
            proc.terminate()
            try:
                proc.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.communicate(timeout=5)
    return {'status':'PASS','passed':len(checks),'checks':checks,'scope':'real local TCP HTTP, disposable SQLite, simulated payments'}


if __name__ == '__main__':
    print(json.dumps(run(), ensure_ascii=False, indent=2))

"""Sustained real HTTP concurrency gate on disposable SQLite, never external DBs.

Run: python scripts/soak_local_http.py --seconds 60 --report soak_report.json
Counters describe repeated requests/invariants, not distinct pytest test cases.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import random
import socket
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.run_phone_demo import demo_environment
from scripts.run_tests_per_file import application_fingerprint


def run(seconds, report, seed=10921):
    if not 1 <= seconds <= 7200:
        raise ValueError('Duration must be between 1 and 7200 seconds')
    rng = random.Random(seed)
    started = time.monotonic()
    source_hash = application_fingerprint(ROOT)
    state = {'status': 'RUNNING', 'started_utc': datetime.now(timezone.utc).isoformat(),
             'scope': 'real loopback HTTP, temporary SQLite, simulated money only',
             'duration_requested_seconds': seconds, 'seed': seed, 'rounds': 0,
             'http_requests': 0, 'invariant_checks': 0, 'scenarios': {},
             'pin_recovery_requests':0,'pin_recoveries':0,'pin_recovery_limited':0,'password_change_races':0,'session_revocation_races':0,
             'application_sha256': source_hash}
    mutex = threading.Lock()

    def save():
        state['elapsed_seconds'] = round(time.monotonic() - started, 2)
        target = Path(report)
        temporary = target.with_suffix('.tmp')
        temporary.write_text(json.dumps(state, ensure_ascii=False, indent=2) + '\n')
        temporary.replace(target)

    def check(condition, message):
        if not condition:
            raise AssertionError(message)
        with mutex:
            state['invariant_checks'] += 1

    import httpx
    with tempfile.TemporaryDirectory(prefix='wp_http_soak_') as folder:
        database = Path(folder) / 'soak.sqlite3'
        env = demo_environment(os.environ, database)
        env['WP_ENABLE_TEST_PAYMENTS'] = '1'
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            port = sock.getsockname()[1]
        with tempfile.TemporaryFile() as log:
            process = subprocess.Popen([sys.executable, '-m', 'uvicorn', 'backend.app:app',
                '--host', '127.0.0.1', '--port', str(port), '--no-access-log'],
                cwd=ROOT, env=env, stdout=log, stderr=log)
            try:
                with httpx.Client(base_url=f'http://127.0.0.1:{port}', trust_env=False, timeout=20) as client:
                    for _ in range(150):
                        if process.poll() is not None:
                            raise RuntimeError('Local HTTP process exited during startup')
                        try:
                            if client.get('/health').status_code == 200:
                                break
                        except httpx.TransportError:
                            pass
                        time.sleep(.1)
                    else:
                        raise TimeoutError('Local HTTP process did not start')

                    def request(method, path, headers=None, body=None, expected=200):
                        response = client.request(method, path, headers=headers, json=body)
                        with mutex:
                            state['http_requests'] += 1
                        check(response.status_code in expected if isinstance(expected, tuple) else response.status_code == expected,
                              f'{method} {path}: unexpected HTTP {response.status_code}')
                        check(response.headers.get('x-content-type-options') == 'nosniff', 'missing security header')
                        return response

                    accounts = {}
                    for name, role in [('farmer', 'rolnik'), ('buyer', 'klient'), ('buyer2', 'klient'),
                                       ('courier', 'dostawca'), ('stranger', 'klient')]:
                        email = name + '@soak.example.invalid'
                        password = 'Disposable-soak-password-123!'
                        uid = request('POST', '/auth/register', body={'email': email, 'password': password, 'role': role}, expected=201).json()['id']
                        token = request('POST', '/auth/login', body={'email': email, 'password': password}).json()['access_token']
                        accounts[name] = ({'Authorization': 'Bearer ' + token}, uid)
                    farmer = accounts['farmer'][0]
                    buyer = accounts['buyer'][0]
                    stranger = accounts['stranger'][0]
                    courier, cid = accounts['courier']
                    products = []
                    initial_stocks = {}
                    for price, fee, stock in [(349, 501, 1), (349, 501, 1000000), (199, 799, 1000000), (123, 457, 1000000)]:
                        pid = request('POST', '/products', farmer, {'name': 'Towar testu obciążenia',
                            'price_grosze': price, 'delivery_grosze': fee, 'stock': stock}, 201).json()['id']
                        products.append(pid)
                        initial_stocks[pid] = stock
                    point = request('POST', '/pickup-points', farmer, {'name': 'Punkt testowy',
                        'city': 'Legnica', 'street': 'Testowa 1', 'opening_hours': '09:00–17:00'}, 201).json()['id']

                    def delivery(pid):
                        return {'product_id': pid, 'quantity': 1, 'fulfillment': 'dostawa',
                                'delivery_city': 'Legnica', 'delivery_street': 'Testowa 1', 'delivery_postal_code': '59-220'}

                    def event(oid, who, kind, event_id=None):
                        return request('POST', f'/test/payments/{oid}/events', who,
                            {'event_id': event_id or uuid4().hex, 'event_type': kind}).json()

                    def invariant_audit():
                        with sqlite3.connect(f'file:{database}?mode=ro', uri=True) as con:
                            check(con.execute('SELECT count(*) FROM products WHERE stock<0 OR typeof(stock)!=\'integer\'').fetchone()[0] == 0,
                                  'invalid inventory')
                            check(con.execute('SELECT count(*) FROM orders WHERE total_grosze!=subtotal_grosze+delivery_grosze OR total_grosze<0').fetchone()[0] == 0,
                                  'invalid order total')
                            check(con.execute('SELECT count(*) FROM payment_simulations WHERE total_grosze!=products_grosze+delivery_grosze OR total_grosze!=seller_grosze+commission_grosze OR (refund_grosze>0 AND payout_grosze>0)').fetchone()[0] == 0,
                                  'invalid financial allocation')
                            check(con.execute("SELECT count(*) FROM payment_simulations p JOIN orders o ON o.id=p.order_id WHERE (p.state='refunded_test' AND (p.refund_grosze!=p.total_grosze OR o.status NOT IN ('anulowane_testowo','nieudana_dostawa_testowo'))) OR (p.state='paid_out_test' AND (p.payout_grosze!=p.seller_grosze OR o.status!='odebrane'))").fetchone()[0] == 0,
                                  'financial/order state mismatch')
                            check(con.execute("SELECT count(*) FROM shipment_groups g WHERE g.delivery_grosze!=(SELECT COALESCE(sum(o.delivery_grosze),0) FROM shipment_order_links l JOIN orders o ON o.id=l.order_id WHERE l.shipment_id=g.id)").fetchone()[0] == 0,
                                  'duplicated shipment fee')
                            con.row_factory=sqlite3.Row
                            from backend.purchase_records import audit_records
                            original_audit=audit_records(con)
                            check(original_audit['ok'], 'original purchase records missing or inconsistent')
                            check(con.execute("SELECT count(*) FROM checkout_idempotency WHERE instr(response_json,'pin_test_only')>0 OR json_extract(response_json,'$.format')!='wp-checkout-aesgcm-v1'").fetchone()[0]==0,
                                  'checkout cache contains plaintext PIN or unsealed reply')
                            counts=con.execute("SELECT count(*) AS n,count(DISTINCT json_extract(response_json,'$.key_id')||':'||json_extract(response_json,'$.nonce')) AS unique_n FROM checkout_idempotency").fetchone()
                            check(counts['n']==counts['unique_n'],'checkout nonce repeated under the same key')
                            check(con.execute('SELECT count(*) FROM checkout_pin_links l JOIN orders o ON o.id=l.order_id WHERE l.buyer_id<>o.buyer_id').fetchone()[0]==0,
                                  'PIN recovery association has wrong owner')
                            check(con.execute("SELECT count(*) FROM checkout_pin_access WHERE attempts<1 OR attempts>5 OR typeof(attempts)<>'integer'").fetchone()[0]==0,
                                  'PIN recovery account budget drift')
                            check(con.execute('SELECT count(*) FROM password_change_access WHERE attempts<1 OR attempts>5').fetchone()[0]==0,
                                  'password change account budget drift')
                            for pid, initial in initial_stocks.items():
                                stock = con.execute('SELECT stock FROM products WHERE id=?', (pid,)).fetchone()[0]
                                reserved = con.execute("SELECT COALESCE(sum(quantity),0) FROM orders WHERE product_id=? AND status!='anulowane_testowo'", (pid,)).fetchone()[0]
                                check(stock + reserved == initial, 'inventory reservation/rollback drift')

                    with ThreadPoolExecutor(max_workers=2) as pool:
                        while time.monotonic() - started < seconds:
                            scenario = state['rounds'] % 5
                            if scenario == 0:
                                headers = {**buyer, 'Idempotency-Key': uuid4().hex}
                                responses = list(pool.map(lambda _: request('POST', '/orders', headers, delivery(products[3]), 201), range(2)))
                                check(responses[0].json() == responses[1].json(), 'idempotency produced two responses')
                                oid = responses[0].json()['id']
                                recovered=request('POST',f'/orders/{oid}/recover-pin-test',buyer,
                                    {'password':'Disposable-soak-password-123!'},(200,429))
                                state['pin_recovery_requests']+=1
                                if recovered.status_code==200:
                                    state['pin_recoveries']+=1
                                    check(recovered.json()['pin_test_only']==responses[0].json()['pin_test_only'] and recovered.json()['order_ids']==[oid],
                                          'recovered a different PIN or purchase')
                                else:
                                    state['pin_recovery_limited']+=1
                                    check(1<=int(recovered.headers['retry-after'])<=900,'invalid recovery retry window')
                                check(recovered.headers.get('cache-control')=='no-store','PIN response is cacheable')
                                request('POST',f'/orders/{oid}/recover-pin-test',stranger,{'password':'Disposable-soak-password-123!'},404)
                                request('POST',f'/orders/{oid}/recover-pin-test',farmer,{'password':'Disposable-soak-password-123!'},403)
                                event(oid, buyer, 'payment_success_test')
                                request('POST', f'/orders/{oid}/cancel-paid-test', stranger, expected=404)
                                results = list(pool.map(lambda _: request('POST', f'/orders/{oid}/cancel-paid-test', buyer).json(), range(2)))
                                check(sorted(r['already_processed'] for r in results) == [False, True], 'double cancellation processed')
                                check(all(r['refund_grosze'] == 580 for r in results), 'incomplete direct refund')
                                record=request('GET',f'/orders/{oid}/purchase-record',buyer).json()
                                check(record['original']['total_grosze']==580 and record['current']['refund_grosze']==580,'direct original/refund mismatch')
                                name = 'concurrent_idempotency_and_cancellation'
                            elif scenario == 1:
                                contenders = [accounts['buyer'][0], accounts['buyer2'][0]]
                                responses = list(pool.map(lambda h: request('POST', '/orders', h, delivery(products[0]), (201, 409)), contenders))
                                check(sorted(r.status_code for r in responses) == [201, 409], 'oversold last unit')
                                winner = next(i for i, r in enumerate(responses) if r.status_code == 201)
                                oid = responses[winner].json()['id']
                                event(oid, contenders[winner], 'payment_success_test')
                                check(request('POST', f'/orders/{oid}/cancel-paid-test', contenders[winner]).json()['refund_grosze'] == 850,
                                      'last-unit refund is incomplete')
                                name = 'competing_buyers_last_unit'
                            elif scenario == 2:
                                quantities = [rng.randint(1, 3), rng.randint(1, 3)]
                                for pid, quantity in zip(products[1:3], quantities):
                                    request('PUT', '/cart/items', buyer, {'product_id': pid, 'quantity': quantity})
                                body = delivery(products[1]); body.pop('product_id'); body.pop('quantity')
                                headers = {**buyer, 'Idempotency-Key': uuid4().hex}
                                responses = list(pool.map(lambda _: request('POST', '/cart/checkout-test', headers, body, 201).json(), range(2)))
                                result = responses[0]
                                check(result == responses[1], 'cart retry duplicated shipment')
                                total = quantities[0] * 349 + quantities[1] * 199 + 799
                                check(result['total_grosze'] == total and result['delivery_grosze'] == 799, 'shipment fee charged per item')
                                for order in result['orders']:
                                    event(order['id'], buyer, 'payment_success_test', 'same-key-for-every-order')
                                sid = result['shipment_id']
                                request('POST', f'/shipments/{sid}/assign-courier-test', farmer, {'courier_id': cid})
                                request('POST', f'/shipments/{sid}/dispatch-test', farmer)
                                request('GET', f'/shipments/{sid}/details', stranger, expected=404)
                                def finish(kind):
                                    if kind == 'refund':
                                        return request('POST', f'/shipments/{sid}/courier-failure-test', farmer,
                                            {'reason': 'dostawca_nie_przyjechal'}, (200, 409))
                                    return request('POST', f'/shipments/{sid}/confirm', courier,
                                        {'pin': result['shipment_pin_test_only'], 'checked_goods': True}, (200, 409))
                                outcomes = list(pool.map(finish, ['refund', 'confirm']))
                                check(sorted(r.status_code for r in outcomes) == [200, 409], 'receipt and refund both succeeded')
                                if outcomes[0].status_code == 200:
                                    check(outcomes[0].json()['refund_grosze'] == total, 'incomplete shipment refund')
                                else:
                                    for order in result['orders']:
                                        event(order['id'], farmer, 'order_completed_test')
                                        paid_out = event(order['id'], farmer, 'weekly_payout_test')
                                        check(paid_out['payout_grosze'] + paid_out['commission_grosze'] == paid_out['total_grosze'], 'payout lost grosze')
                                check(request('GET', '/couriers/me/active-addresses', courier).json() == [], 'courier address survived terminal state')
                                record=request('GET',f'/shipments/{sid}/purchase-record',buyer).json()
                                check(record['original_available'] and record['original']['total_grosze']==total and record['original']['delivery_grosze']==799,'shipment original terms drift')
                                check(all('pin_test_only' not in str(item) and 'delivery_street' not in str(item) for item in record['orders']),'private record contains PIN/address')
                                name = 'shipment_fee_and_concurrent_pin_refund'
                            elif scenario == 3:
                                headers = accounts['buyer2'][0]
                                result = request('POST', '/orders', headers, {'product_id': products[3], 'quantity': 1,
                                    'fulfillment': 'odbior', 'pickup_point_id': point}, 201).json()
                                oid = result['id']; pin = result['pin_test_only']
                                event(oid, headers, 'payment_success_test')
                                request('POST', f'/test/orders/{oid}/ready', farmer)
                                wrong = '999999' if pin != '999999' else '888888'
                                check(request('POST', f'/orders/{oid}/confirm', farmer,
                                    {'pin': wrong, 'checked_goods': True}).json()['remaining_attempts'] == 4, 'wrong PIN not counted')
                                request('POST', f'/orders/{oid}/confirm', farmer, {'pin': pin, 'checked_goods': False}, 422)
                                check(request('POST', f'/orders/{oid}/confirm', farmer, {'pin': pin, 'checked_goods': True}).json()['confirmed'], 'valid PIN rejected')
                                request('POST', f'/orders/{oid}/confirm', farmer, {'pin': pin, 'checked_goods': True}, 409)
                                event(oid, farmer, 'order_completed_test')
                                event(oid, farmer, 'weekly_payout_test')
                                record=request('GET',f'/orders/{oid}/purchase-record',headers).json()
                                check(record['original']['pickup_point']['id']==point and record['original']['delivery_grosze']==0,'pickup original terms drift')
                                check(record['current']['status']=='odebrane' and record['current']['payment_state_test']=='paid_out_test','pickup record current state drift')
                                name = 'pickup_pin_payment_and_payout'
                            else:
                                body = {'email': 'buyer@soak.example.invalid', 'password': 'Disposable-soak-password-123!'}
                                extra = {'Authorization': 'Bearer ' + request('POST', '/auth/login', body=body).json()['access_token']}
                                request('POST', '/auth/logout', extra)
                                request('GET', '/auth/me', extra, expected=401)
                                request('GET', '/orders/1/purchase-record', extra, expected=401)
                                request('GET', '/auth/me', buyer)
                                request('POST', '/products', buyer, {'name': 'Zakazany', 'price_grosze': 1, 'delivery_grosze': 0, 'stock': 1}, 403)
                                request('POST', '/products', farmer, {'name': 'Ułamek', 'price_grosze': 1.0, 'delivery_grosze': 0, 'stock': 1}, 422)
                                name = 'session_revocation_roles_and_strict_money'
                            state['rounds'] += 1
                            state['scenarios'][name] = state['scenarios'].get(name, 0) + 1
                            if state['rounds'] % 100 == 0:
                                email=uuid4().hex+'@password-soak.example.invalid'
                                old='Disposable-password-race-old!';new='Disposable-password-race-new!'
                                request('POST','/auth/register',body={'email':email,'password':old,'role':'klient'},expected=201)
                                access=request('POST','/auth/login',body={'email':email,'password':old}).json()['access_token']
                                headers={'Authorization':'Bearer '+access}
                                def password_race(kind):
                                    if kind=='change':
                                        return request('POST','/auth/change-password',headers,
                                            {'current_password':old,'new_password':new})
                                    return request('POST','/auth/login',body={'email':email,'password':old},expected=(200,401))
                                changed,old_login=list(pool.map(password_race,['change','login']))
                                check(changed.json()=={'changed':True,'reauthentication_required':True},'password change result differs')
                                request('GET','/auth/me',headers,expected=401)
                                if old_login.status_code==200:
                                    request('GET','/auth/me',{'Authorization':'Bearer '+old_login.json()['access_token']},expected=401)
                                fresh=request('POST','/auth/login',body={'email':email,'password':new}).json()['access_token']
                                request('GET','/auth/me',{'Authorization':'Bearer '+fresh})
                                request('POST','/auth/logout',{'Authorization':'Bearer '+fresh})
                                state['password_change_races']+=1
                                # Independent two-session race. Exactly one device survives.
                                first=request('POST','/auth/login',body={'email':email,'password':new}).json()['access_token']
                                second=request('POST','/auth/login',body={'email':email,'password':new}).json()['access_token']
                                devices=[{'Authorization':'Bearer '+value} for value in (first,second)]
                                overview=request('GET','/auth/sessions',devices[0]).json()
                                check(overview['active_sessions']==2 and overview['other_sessions']==1,'incorrect private session count')
                                check(set(overview)=={'active_sessions','other_sessions','current_expires_at'},'session overview leaks extra data')
                                results=list(pool.map(lambda device:request('POST','/auth/logout-others',device,expected=(200,401)),devices))
                                check(sorted(r.status_code for r in results)==[200,401],'both devices survived mutual revocation')
                                survivor=devices[next(i for i,r in enumerate(results) if r.status_code==200)]
                                loser=devices[next(i for i,r in enumerate(results) if r.status_code==401)]
                                request('GET','/auth/me',loser,expected=401)
                                check(request('GET','/auth/sessions',survivor).json()['active_sessions']==1,'wrong survivor count')
                                request('POST','/auth/logout-all',survivor)
                                request('GET','/auth/me',survivor,expected=401)
                                state['session_revocation_races']+=1
                            if state['rounds'] % 25 == 0:
                                invariant_audit()
                                save()
                                print(json.dumps({k: state[k] for k in ('rounds', 'http_requests', 'invariant_checks', 'elapsed_seconds')}), flush=True)
                        invariant_audit()
                    check(application_fingerprint(ROOT) == source_hash, 'runtime sources changed during soak')
                    state['status'] = 'PASS'
            except Exception as exc:
                state['status'] = 'FAIL'
                state['error'] = f'{type(exc).__name__}: {exc}'
            finally:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill(); process.wait(timeout=5)
                state['finished_utc'] = datetime.now(timezone.utc).isoformat()
                save()
    return state


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seconds', type=int, default=60)
    parser.add_argument('--report', default='soak_report.json')
    parser.add_argument('--seed', type=int, default=10921)
    args = parser.parse_args()
    result = run(args.seconds, ROOT / args.report, args.seed)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result['status'] == 'PASS' else 1)

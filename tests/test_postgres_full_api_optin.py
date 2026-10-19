"""Opt-in native PostgreSQL + restricted application role + real TCP HTTP.

Requires a disposable test-cluster DSN with CREATE DATABASE/ROLE permissions.
Creates and drops ONLY a new randomly named database and role. Never uses Neon.
"""
from concurrent.futures import ThreadPoolExecutor
import hashlib
from pathlib import Path
import os
import secrets
import socket
import subprocess
import sys
import tempfile
import time
from uuid import uuid4

import httpx
import pytest

ROOT = Path(__file__).resolve().parents[1]


def reviewed_test_schema(root):
    """Read a verified, ordered SQL snapshot before creating any test resource."""
    from database.verify_test_migrations import verify
    reviewed = verify(root)
    if not reviewed['ok']:
        raise ValueError('Test migration review failed; no database created')
    statements = []
    for entry in reviewed['files']:
        content = (root / entry['file']).read_bytes()
        if hashlib.sha256(content).hexdigest() != entry['sha256']:
            raise ValueError('Test migrations changed during review; no database created')
        statements.append(content.decode('utf-8'))
    return tuple(statements)


class NativeAPI:
    """Preserve two-value unpacking while permitting a controlled process restart."""
    def __init__(self, client, parameters, restart, key_path, reset_outbox=None):
        self.client = client
        self.parameters = parameters
        self.restart = restart
        self.key_path = key_path
        self.reset_outbox = reset_outbox

    def __iter__(self):
        return iter((self.client, self.parameters))


@pytest.fixture(scope='module')
def pg_api():
    yield from _postgres_api()


@pytest.fixture
def pg_restart_api():
    # Restart scenarios get a separate database and key, independent of tests
    # that intentionally corrupt encrypted rows to exercise access controls.
    yield from _postgres_api()


@pytest.fixture
def pg_reset_api():
    yield from _postgres_api(reset=True)


def _postgres_api(*, reset=False):
    dsn = os.environ.get('WP_TEST_POSTGRES_DSN')
    if not dsn:
        pytest.skip('Native PostgreSQL API gate not executed: WP_TEST_POSTGRES_DSN absent')
    from backend.postgres_test_guard import require_disposable_postgres
    from urllib.parse import urlsplit
    require_disposable_postgres(dsn)
    host = urlsplit(dsn).hostname
    if host not in ('localhost', '127.0.0.1', '::1', 'postgres'):
        raise ValueError('This gate accepts only loopback or the local Compose postgres service')
    migration_sql = reviewed_test_schema(ROOT / 'database')
    psycopg = pytest.importorskip('psycopg')
    from psycopg import sql
    from psycopg.conninfo import conninfo_to_dict, make_conninfo
    from scripts.run_phone_demo import demo_environment

    suffix = uuid4().hex
    database = 'wp_test_' + suffix
    role = 'wp_test_app_' + suffix
    password = secrets.token_hex(24)
    parameters = conninfo_to_dict(dsn)
    admin_parameters = {**parameters, 'dbname': database}
    app_parameters = {**admin_parameters, 'user': role, 'password': password}
    app_dsn = make_conninfo(**app_parameters)
    role_created = database_created = False
    with psycopg.connect(dsn, autocommit=True, connect_timeout=5) as admin:
        process = None
        try:
            admin.execute(sql.SQL('CREATE ROLE {} LOGIN PASSWORD {} NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOREPLICATION NOBYPASSRLS').format(
                sql.Identifier(role), sql.Literal(password)))
            role_created = True
            admin.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(database)))
            database_created = True
            with psycopg.connect(**admin_parameters, autocommit=True) as migration:
                for statement in migration_sql:
                    migration.execute(statement)
                migration.execute('REVOKE CREATE ON SCHEMA public FROM PUBLIC')
                migration.execute(sql.SQL('GRANT CONNECT ON DATABASE {} TO {}').format(
                    sql.Identifier(database), sql.Identifier(role)))
                migration.execute(sql.SQL('GRANT USAGE ON SCHEMA public TO {}').format(sql.Identifier(role)))
                migration.execute(sql.SQL('GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA public TO {}').format(sql.Identifier(role)))
                migration.execute(sql.SQL('GRANT USAGE,SELECT ON ALL SEQUENCES IN SCHEMA public TO {}').format(sql.Identifier(role)))

            with socket.socket() as sock:
                sock.bind(('127.0.0.1', 0))
                port = sock.getsockname()[1]
            with tempfile.TemporaryDirectory(prefix='wp_pg_api_') as folder:
                env = demo_environment(os.environ, Path(folder) / 'unused.sqlite3')
                from backend.checkout_vault import create_ring
                keyfile=Path(folder)/'api.checkout-key';create_ring(keyfile)
                env.update(DATABASE_URL=app_dsn, WP_ENV='test', WP_ENABLE_TEST_PAYMENTS='1',WP_CHECKOUT_KEY_FILE=str(keyfile))
                env.pop('WP_AUTO_INIT_POSTGRES', None)
                reset_outbox = Path(folder)/'reset-outbox' if reset else None
                if reset:
                    env.update(WP_ENABLE_TEST_PASSWORD_RESET='1', WP_ENABLE_PG_TEST_PASSWORD_RESET='1',
                               WP_TEST_RESET_OUTBOX=str(reset_outbox))
                with tempfile.TemporaryFile() as log:
                    with httpx.Client(base_url=f'http://127.0.0.1:{port}', trust_env=False, timeout=15) as client:
                        def start():
                            nonlocal process
                            process = subprocess.Popen([
                                sys.executable, '-m', 'uvicorn', 'backend.app:app', '--host', '127.0.0.1',
                                '--port', str(port), '--no-access-log'], cwd=ROOT, env=env,
                                stdout=log, stderr=log)
                            for _ in range(150):
                                if process.poll() is not None:
                                    raise RuntimeError('Native PostgreSQL API server failed to start')
                                try:
                                    if client.get('/health').status_code == 200:
                                        return
                                except httpx.TransportError:
                                    pass
                                time.sleep(.1)
                            raise TimeoutError('Native PostgreSQL API server startup timed out')

                        def restart():
                            process.terminate()
                            try:
                                process.wait(timeout=10)
                            except subprocess.TimeoutExpired:
                                process.kill();process.wait(timeout=5)
                            start()

                        start()
                        yield NativeAPI(client, app_parameters, restart, keyfile, reset_outbox)
        finally:
            if process is not None:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
            if database_created:
                admin.execute(sql.SQL('DROP DATABASE {} WITH (FORCE)').format(sql.Identifier(database)))
            if role_created:
                admin.execute(sql.SQL('DROP ROLE {}').format(sql.Identifier(role)))


def register(client, role):
    email = uuid4().hex + '@example.invalid'
    password = secrets.token_urlsafe(24)
    response = client.post('/auth/register', json={'email': email, 'password': password, 'role': role})
    assert response.status_code == 201, response.text
    uid = response.json()['id']
    login = client.post('/auth/login', json={'email': email, 'password': password})
    assert login.status_code == 200, login.text
    return {'Authorization': 'Bearer ' + login.json()['access_token']}, uid


def product(client, farmer, stock=10):
    response = client.post('/products', headers=farmer, json={
        'name': 'Warzywa PostgreSQL', 'price_grosze': 349, 'delivery_grosze': 501, 'stock': stock})
    assert response.status_code == 201, response.text
    return response.json()['id']


def delivery(pid):
    return {'product_id': pid, 'quantity': 1, 'fulfillment': 'dostawa',
            'delivery_city': 'Legnica', 'delivery_street': 'Testowa 1', 'delivery_postal_code': '59-220'}


def test_native_application_role_has_no_administrative_privileges(pg_api):
    _, parameters = pg_api
    import psycopg
    with psycopg.connect(**parameters) as con:
        row = con.execute('SELECT rolsuper,rolcreatedb,rolcreaterole,rolbypassrls FROM pg_roles WHERE rolname=current_user').fetchone()
        assert row == (False, False, False, False)
        assert con.execute("SELECT count(*) FROM information_schema.tables WHERE table_schema='public'").fetchone()[0] >= 28
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            con.execute('CREATE TABLE forbidden_application_ddl (id integer)')


def test_native_concurrent_idempotency_and_full_refund(pg_api):
    client, parameters = pg_api
    farmer, _ = register(client, 'rolnik')
    buyer, _ = register(client, 'klient')
    pid = product(client, farmer)
    headers = {**buyer, 'Idempotency-Key': uuid4().hex}
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(lambda _: client.post('/orders', headers=headers, json=delivery(pid)), range(2)))
    assert [r.status_code for r in responses] == [201, 201], [r.text for r in responses]
    assert responses[0].json() == responses[1].json()
    oid = responses[0].json()['id']
    paid = client.post(f'/test/payments/{oid}/events', headers=buyer,
                       json={'event_id': uuid4().hex, 'event_type': 'payment_success_test'})
    assert paid.status_code == 200, paid.text
    for retry in range(2):
        response = client.post(f'/orders/{oid}/cancel-paid-test', headers=buyer)
        assert response.status_code == 200, response.text
        assert response.json()['refund_grosze'] == 850
        assert response.json()['already_processed'] is bool(retry)
    import psycopg
    with psycopg.connect(**parameters) as con:
        assert con.execute('SELECT stock FROM products WHERE id=%s', (pid,)).fetchone()[0] == 10
        assert con.execute('SELECT count(*) FROM orders WHERE product_id=%s', (pid,)).fetchone()[0] == 1


def test_native_competing_buyers_do_not_oversell(pg_api):
    client, parameters = pg_api
    farmer, _ = register(client, 'rolnik')
    buyers = [register(client, 'klient')[0] for _ in range(2)]
    pid = product(client, farmer, stock=1)
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(lambda h: client.post('/orders', headers=h, json=delivery(pid)), buyers))
    assert sorted(r.status_code for r in responses) == [201, 409]
    import psycopg
    with psycopg.connect(**parameters) as con:
        assert con.execute('SELECT stock FROM products WHERE id=%s', (pid,)).fetchone()[0] == 0


def test_native_multi_item_shipping_refund_and_address_revocation(pg_api):
    client, parameters = pg_api
    farmer, _ = register(client, 'rolnik')
    buyer, _ = register(client, 'klient')
    courier, cid = register(client, 'dostawca')
    products = [product(client, farmer) for _ in range(2)]
    for pid in products:
        assert client.put('/cart/items', headers=buyer, json={'product_id': pid, 'quantity': 2}).status_code == 200
    body = delivery(products[0])
    body.pop('product_id'); body.pop('quantity')
    checkout = client.post('/cart/checkout-test', headers={**buyer, 'Idempotency-Key': uuid4().hex}, json=body)
    assert checkout.status_code == 201, checkout.text
    result = checkout.json()
    assert result['delivery_grosze'] == 501 and result['total_grosze'] == 1897
    for order in result['orders']:
        assert client.post(f'/test/payments/{order["id"]}/events', headers=buyer,
                           json={'event_id': 'same-external-key', 'event_type': 'payment_success_test'}).status_code == 200
    sid = result['shipment_id']
    assert client.post(f'/shipments/{sid}/assign-courier-test', headers=farmer, json={'courier_id': cid}).status_code == 200
    assert client.post(f'/shipments/{sid}/dispatch-test', headers=farmer).status_code == 200
    assert len(client.get('/couriers/me/active-addresses', headers=courier).json()) == 2
    response = client.post(f'/shipments/{sid}/courier-failure-test', headers=farmer, json={'reason': 'dostawca_nie_przyjechal'})
    assert response.status_code == 200, response.text
    assert response.json()['refund_grosze'] == 1897
    assert client.get('/couriers/me/active-addresses', headers=courier).json() == []
    assert client.post(f'/shipments/{sid}/confirm', headers=courier,
                       json={'pin': result['shipment_pin_test_only'], 'checked_goods': True}).status_code == 409


def test_native_inventory_expiration_transaction_and_payment_guard(pg_api):
    """Native gate only; no SQLite adapter is accepted as evidence for this case."""
    from datetime import datetime, timedelta, timezone
    from backend.pg_adapter import postgres_db
    from backend.inventory_reservations import expire_due
    from psycopg.conninfo import make_conninfo
    client, parameters = pg_api
    farmer, _ = register(client, 'rolnik')
    buyer, _ = register(client, 'klient')
    pid = product(client, farmer)
    receipt = client.post('/orders', headers=buyer, json=delivery(pid))
    assert receipt.status_code == 201, receipt.text
    oid = receipt.json()['id']
    deadline = datetime.now(timezone.utc)-timedelta(seconds=1)
    with postgres_db(make_conninfo(**parameters)) as con:
        con.execute('UPDATE inventory_reservations SET expires_at=? WHERE order_id=?', (deadline.isoformat(), oid))
    late = client.post(f'/test/payments/{oid}/events', headers=buyer,
                       json={'event_id': uuid4().hex, 'event_type': 'payment_success_test'})
    assert late.status_code == 409
    def expired_event(con, order_id, actor_id, kind, old, new):
        assert order_id == oid and kind == 'reservation_expired_test'
    for _ in range(2):
        with postgres_db(make_conninfo(**parameters)) as con:
            expire_due(con, now=datetime.now(timezone.utc), postgres=True, record_event=expired_event)
    with postgres_db(make_conninfo(**parameters)) as con:
        assert con.execute('SELECT stock FROM products WHERE id=?', (pid,)).fetchone()['stock'] == 10
        assert con.execute('SELECT status FROM orders WHERE id=?', (oid,)).fetchone()['status'] == 'anulowane_testowo'
        assert con.execute('SELECT state FROM payment_simulations WHERE order_id=?', (oid,)).fetchone() is None


def test_native_local_marketplace_and_point_contract(pg_api):
    """Real PostgreSQL gate for vector SQL, Polish names and point write locks."""
    client,_=pg_api
    farmer,_=register(client,'rolnik');buyer,_=register(client,'klient')
    pid=product(client,farmer)
    renamed=client.patch(f'/products/mine/{pid}',headers=farmer,json={'name':'ŁĄKOWE ŚLIWKI'})
    assert renamed.status_code==200,renamed.text
    body={'name':'Punkt PostgreSQL','city':'Opole','street':'Polna 1','opening_hours':'9:00–17:00',
          'latitude_e6':52_000_000,'longitude_e6':16_000_000}
    response=client.post('/pickup-points',headers=farmer,json=body)
    assert response.status_code==201,response.text
    point=response.json()['id']
    offers=client.post('/marketplace/nearby',json={'latitude_e6':52_000_000,'longitude_e6':16_000_000,
        'radius_m':100,'q':'lakowe sliwki'})
    assert offers.status_code==200,offers.text
    assert any(i['product']['id']==pid and i['pickup_point']['id']==point and i['distance_m']==0 for i in offers.json()['items'])
    assert client.put(f'/pickup-points/{point}',headers=buyer,json={**body,'active':False}).status_code==403
    order=client.post('/orders',headers=buyer,json={'product_id':pid,'quantity':1,'fulfillment':'odbior','pickup_point_id':point})
    assert order.status_code==201,order.text
    assert client.put(f'/pickup-points/{point}',headers=farmer,json={**body,'active':True,'street':'Inna 99'}).status_code==409
    assert client.put(f'/pickup-points/{point}',headers=farmer,json={**body,'active':False}).status_code==200
    assert client.post(f'/orders/{order.json()["id"]}/cancel-test',headers=buyer).status_code==200


def test_native_purchase_record_is_private_and_insert_only(pg_api):
    """Requires real PostgreSQL and the restricted non-owner application role."""
    client,parameters=pg_api
    farmer,_=register(client,'rolnik');buyer,_=register(client,'klient');other,_=register(client,'klient')
    pid=product(client,farmer)
    checkout=client.post('/orders',headers=buyer,json=delivery(pid))
    assert checkout.status_code==201,checkout.text
    oid=checkout.json()['id'];url=f'/orders/{oid}/purchase-record'
    original=client.get(url,headers=buyer)
    assert original.status_code==200,original.text
    assert original.json()['original']['product']['unit_price_grosze']==349
    assert original.headers['cache-control']=='no-store'
    assert client.get(url,headers=other).status_code==404
    assert client.patch(f'/products/mine/{pid}',headers=farmer,json={'name':'Późniejsza oferta','price_grosze':9999}).status_code==200
    assert client.get(url,headers=farmer).json()['original']==original.json()['original']
    import psycopg
    for statement in ('UPDATE order_purchase_records SET product_name=%s WHERE order_id=%s',
                      'DELETE FROM order_purchase_records WHERE order_id=%s'):
        with pytest.raises(psycopg.IntegrityError):
            with psycopg.connect(**parameters) as con:
                con.execute(statement,('Niedozwolona zmiana',oid) if statement.startswith('UPDATE') else (oid,))
    assert client.get(url,headers=buyer).json()==original.json()


def test_native_checkout_reply_is_sealed_and_bound_to_buyer(pg_api):
    client,parameters=pg_api
    farmer,_=register(client,'rolnik');buyer,bid=register(client,'klient');other,other_id=register(client,'klient')
    pid=product(client,farmer);body=delivery(pid);key=uuid4().hex
    original=client.post('/orders',headers={**buyer,'Idempotency-Key':key},json=body)
    assert original.status_code==201,original.text
    second=client.post('/orders',headers={**other,'Idempotency-Key':key},json=body)
    assert second.status_code==201,second.text
    import json,psycopg
    with psycopg.connect(**parameters) as con:
        raw=con.execute('SELECT response_json FROM checkout_idempotency WHERE buyer_id=%s AND request_key=%s',(bid,'direct:'+key)).fetchone()[0]
        assert json.loads(raw)['format']=='wp-checkout-aesgcm-v1' and 'pin_test_only' not in raw
        con.execute('UPDATE checkout_idempotency SET response_json=%s WHERE buyer_id=%s AND request_key=%s',(raw,other_id,'direct:'+key))
    replay=client.post('/orders',headers={**other,'Idempotency-Key':key},json=body)
    assert replay.status_code==409 and 'pin_test_only' not in replay.text
    assert client.post('/orders',headers={**buyer,'Idempotency-Key':key},json=body).json()==original.json()


def test_native_long_direct_key_and_password_protected_recovery(pg_api):
    client,parameters=pg_api
    farmer,_=register(client,'rolnik');buyer,bid=register(client,'klient')
    password='Disposable-PG-PIN-recovery-123!'
    from argon2 import PasswordHasher
    import psycopg
    with psycopg.connect(**parameters) as con:
        con.execute('UPDATE users SET password_hash=%s WHERE id=%s',(PasswordHasher().hash(password),bid))
    pid=product(client,farmer);key='k'*100
    response=client.post('/orders',headers={**buyer,'Idempotency-Key':key},json=delivery(pid))
    assert response.status_code==201,response.text
    url=f'/orders/{response.json()["id"]}/recover-pin-test'
    recovered=client.post(url,headers=buyer,json={'password':password})
    assert recovered.status_code==200,recovered.text
    assert recovered.json()['pin_test_only']==response.json()['pin_test_only']
    for _ in range(4):assert client.post(url,headers=buyer,json={'password':'wrong'}).status_code==401
    assert client.post(url,headers=buyer,json={'password':password}).status_code==429
    assert client.post(url,headers=farmer,json={'password':password}).status_code==403


def test_native_password_change_serializes_with_old_password_login(pg_api):
    client,_=pg_api
    email=uuid4().hex+'@example.invalid';old='Disposable-PG-old-password!';new='Disposable-PG-new-password!'
    assert client.post('/auth/register',json={'email':email,'password':old,'role':'klient'}).status_code==201
    logged=client.post('/auth/login',json={'email':email,'password':old});assert logged.status_code==200
    headers={'Authorization':'Bearer '+logged.json()['access_token']}
    def run(kind):
        if kind=='change':return client.post('/auth/change-password',headers=headers,json={'current_password':old,'new_password':new})
        return client.post('/auth/login',json={'email':email,'password':old})
    with ThreadPoolExecutor(max_workers=2) as pool:changed,login=list(pool.map(run,['change','login']))
    assert changed.status_code==200,changed.text
    assert login.status_code in (200,401)
    if login.status_code==200:assert client.get('/auth/me',headers={'Authorization':'Bearer '+login.json()['access_token']}).status_code==401
    assert client.get('/auth/me',headers=headers).status_code==401
    assert client.post('/auth/login',json={'email':email,'password':old}).status_code==401
    assert client.post('/auth/login',json={'email':email,'password':new}).status_code==200


def test_native_session_revocation_serializes_two_devices(pg_api):
    client,_=pg_api
    email=uuid4().hex+'@example.invalid';password='Disposable-PG-session-password!'
    assert client.post('/auth/register',json={'email':email,'password':password,'role':'klient'}).status_code==201
    devices=[]
    for _ in range(2):
        login=client.post('/auth/login',json={'email':email,'password':password});assert login.status_code==200
        devices.append({'Authorization':'Bearer '+login.json()['access_token']})
    overview=client.get('/auth/sessions',headers=devices[0]);assert overview.status_code==200,overview.text
    assert overview.json()['active_sessions']==2 and overview.json()['other_sessions']==1
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(lambda h:client.post('/auth/logout-others',headers=h),devices))
    assert sorted(r.status_code for r in results)==[200,401]
    winner=devices[next(i for i,r in enumerate(results) if r.status_code==200)]
    loser=devices[next(i for i,r in enumerate(results) if r.status_code==401)]
    assert client.get('/auth/me',headers=loser).status_code==401
    assert client.get('/auth/sessions',headers=winner).json()['active_sessions']==1
    assert client.post('/auth/logout-all',headers=winner).status_code==200
    assert client.get('/auth/me',headers=winner).status_code==401


def test_native_seller_reminder_counts_received_shipment_once(pg_api):
    from tests.test_seller_profile_reminder import exercise_completed_shipment
    client,_=pg_api
    exercise_completed_shipment(client)


def test_native_admin_seller_queue_and_concurrent_stale_decisions(pg_api):
    import psycopg
    from tests.test_admin_seller_review import create_admin,exercise_admin_review
    client,parameters=pg_api
    def promote(uid):
        with psycopg.connect(**parameters) as con:
            con.execute("UPDATE users SET role='admin' WHERE id=%s",(uid,))
    admin,_=create_admin(client,promote)
    fid=exercise_admin_review(client,admin)
    with psycopg.connect(**parameters) as con:
        assert con.execute("SELECT COUNT(*) FROM seller_compliance_events WHERE farmer_id=%s AND event_type LIKE 'review_%%'",(fid,)).fetchone()[0]==1


def test_native_private_support_cases(pg_api):
    from tests.test_support_cases_http import exercise_support
    from tests.test_admin_seller_review import create_admin
    import psycopg
    client,parameters=pg_api
    def promote(uid):
        with psycopg.connect(**parameters) as con:con.execute("UPDATE users SET role='admin' WHERE id=%s",(uid,))
    admin,_=create_admin(client,promote)
    exercise_support(client,admin)


def test_private_preview_probe_with_restricted_role(pg_api, tmp_path):
    """A real disposable PostgreSQL probe must run inside a read-only transaction."""
    _, parameters = pg_api
    from urllib.parse import quote
    from backend.checkout_vault import create_ring
    from scripts.check_postgres_preview import inspect_preview
    import psycopg
    key = tmp_path/'preview.checkout-key';create_ring(key)
    host = parameters['host']
    if host == '::1':host = '[::1]'
    dsn = ('postgresql://' + quote(parameters['user'], safe='') + ':' +
           quote(parameters['password'], safe='') + '@' + host + ':' +
           str(parameters.get('port', '5432')) + '/' + parameters['dbname'])
    observed = []
    def connect(*args, **kwargs):
        con = psycopg.connect(*args, **kwargs)
        try:
            assert con.execute('SHOW transaction_read_only').fetchone()[0] == 'on'
        except BaseException:
            con.close();raise
        observed.append(True)
        return con
    report = inspect_preview({'WP_ENV': 'test', 'WP_TEST_DATABASE_URL': dsn,
        'WP_CHECKOUT_KEY_FILE': str(key)}, connect=connect)
    assert observed and report['success'] and report['database_core_checked']
    assert not report['preview_started'] and not report['ready_for_production']


@pytest.mark.parametrize('kind', ['direct', 'shipment'])
def test_native_purchase_survives_process_restart(pg_restart_api, kind):
    """Same DB and encryption key: stable session, PIN, stock and idempotency."""
    client, parameters = pg_restart_api
    farmer, _ = register(client, 'rolnik')
    buyer, buyer_id = register(client, 'klient')
    products = [product(client, farmer, stock=5) for _ in range(1 if kind == 'direct' else 2)]
    key = uuid4().hex
    headers = {**buyer, 'Idempotency-Key': key}
    if kind == 'direct':
        path = '/orders';body = delivery(products[0]);record_key = 'direct:'+key
    else:
        for pid in products:
            assert client.put('/cart/items', headers=buyer,
                json={'product_id': pid, 'quantity': 1}).status_code == 200
        path = '/cart/checkout-test';body = delivery(products[0]);record_key = key
        body.pop('product_id');body.pop('quantity')
    response = client.post(path, headers=headers, json=body)
    assert response.status_code == 201
    original = response.json()
    ids = [original['id']] if kind == 'direct' else [x['id'] for x in original['orders']]
    if kind == 'shipment':
        assert original['delivery_grosze'] == 501
        for oid in ids:
            assert client.post(f'/test/payments/{oid}/events', headers=buyer,
                json={'event_id': uuid4().hex, 'event_type': 'payment_success_test'}).status_code == 200
    import psycopg
    def snapshot():
        with psycopg.connect(**parameters) as con:
            return (
                con.execute('SELECT id,status,total_grosze FROM orders WHERE buyer_id=%s ORDER BY id', (buyer_id,)).fetchall(),
                con.execute('SELECT id,stock FROM products WHERE id=ANY(%s) ORDER BY id', (products,)).fetchall(),
                con.execute('SELECT order_id,state,total_grosze,refund_grosze FROM payment_simulations WHERE order_id=ANY(%s) ORDER BY order_id', (ids,)).fetchall(),
                con.execute('SELECT response_json FROM checkout_idempotency WHERE buyer_id=%s AND request_key=%s', (buyer_id, record_key)).fetchone(),
            )
    before = snapshot()
    records = [client.get(f'/orders/{oid}/purchase-record', headers=buyer).json() for oid in ids]
    pg_restart_api.restart()
    assert client.get('/auth/me', headers=buyer).status_code == 200
    replay = client.post(path, headers=headers, json=body)
    assert replay.status_code == 201 and replay.json() == original
    assert snapshot() == before
    assert [client.get(f'/orders/{oid}/purchase-record', headers=buyer).json() for oid in ids] == records
    changed = {**body, 'delivery_street': 'Inny adres testowy 123'}
    assert client.post(path, headers=headers, json=changed).status_code == 409
    assert snapshot() == before


def test_native_encrypted_postgres_backup_and_isolated_restore(pg_restart_api, tmp_path):
    """Restore real dump + original vault key without altering the live source."""
    from urllib.parse import quote
    import psycopg
    from scripts.postgres_test_backup import backup, rehearse, make_backup_key
    client, parameters = pg_restart_api
    farmer, _ = register(client, 'rolnik')
    buyer, _ = register(client, 'klient')
    pid = product(client, farmer, stock=3)
    headers = {**buyer, 'Idempotency-Key': uuid4().hex}
    response = client.post('/orders', headers=headers, json=delivery(pid))
    assert response.status_code == 201
    original = response.json()
    assert client.post(f"/test/payments/{original['id']}/events", headers=buyer,
        json={'event_id': uuid4().hex, 'event_type': 'payment_success_test'}).status_code == 200
    host = parameters['host']
    if host == '::1':host = '[::1]'
    dsn = ('postgresql://' + quote(parameters['user'], safe='') + ':' +
           quote(parameters['password'], safe='') + '@' + host + ':' +
           str(parameters.get('port', '5432')) + '/' + parameters['dbname'])
    keys = tmp_path/'keys';keys.mkdir()
    archives = tmp_path/'archives';archives.mkdir()
    key = keys/'independent.backup-key';make_backup_key(key)
    archive = archives/'postgres.wpbackup'
    with psycopg.connect(**parameters) as source:
        before = source.execute('SELECT count(*) FROM sessions').fetchone()[0]
    assert backup(dsn, pg_restart_api.key_path, key, archive)['encrypted_backup']
    assert b'PGDMP' not in archive.read_bytes()[:64]
    result = rehearse(archive, key, os.environ['WP_TEST_POSTGRES_DSN'])
    assert result == {'orders_checked': 1, 'checkout_replies_checked': 1,
        'sessions_revoked': before, 'success': True, 'restore_verified': True,
        'rehearsal_database_removed': True, 'application_started': False}
    with psycopg.connect(**parameters) as source:
        assert source.execute('SELECT count(*) FROM sessions').fetchone()[0] == before
    assert client.get('/auth/me', headers=buyer).status_code == 200
    replay = client.post('/orders', headers=headers, json=delivery(pid))
    assert replay.status_code == 201 and replay.json() == original


def test_native_reset_replay_restart_and_purchase_integrity(pg_reset_api):
    import psycopg
    from tests.test_password_reset_http import register as reset_register, request, confirm, EMAIL, OLD, NEW
    client, parameters = pg_reset_api
    assert client.get('/auth/password-reset-test/options').json()['enabled']
    farmer, _ = register(client, 'rolnik')
    buyer = reset_register(client)
    pid = product(client, farmer)
    order = client.post('/orders', headers={**buyer,'Idempotency-Key':uuid4().hex}, json=delivery(pid))
    assert order.status_code == 201
    oid = order.json()['id']
    record = client.get(f'/orders/{oid}/purchase-record', headers=buyer).json()
    second = client.post('/auth/login', json={'email':EMAIL,'password':OLD}).json()['access_token']
    token, notice = request(client, pg_reset_api.reset_outbox)
    unknown, unknown_notice = request(client, pg_reset_api.reset_outbox, 'unknown@example.invalid')
    assert notice == unknown_notice and confirm(client, unknown).status_code == 400
    expired,_ = request(client, pg_reset_api.reset_outbox)
    with psycopg.connect(**parameters) as con:
        con.execute('UPDATE password_reset_tokens SET expires_at=%s WHERE token_hash=%s',
                    ('2000-01-01T00:00:00+00:00',hashlib.sha256(expired.encode()).hexdigest()))
    assert confirm(client,expired).status_code == 400
    with psycopg.connect(**parameters) as con:
        stored = con.execute('SELECT token_hash FROM password_reset_tokens WHERE token_hash=%s',
                             (hashlib.sha256(token.encode()).hexdigest(),)).fetchone()[0]
        assert stored == hashlib.sha256(token.encode()).hexdigest() and stored != token
        before = con.execute('SELECT id,status,total_grosze,pin_hash FROM orders').fetchall()
    pg_reset_api.restart()
    assert client.get('/auth/me',headers=buyer).status_code == 200
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(lambda _:confirm(client,token).status_code, range(2))) == [200,400]
    for headers in (buyer, {'Authorization':'Bearer '+second}):
        assert client.get('/auth/me',headers=headers).status_code == 401
    assert client.post('/auth/login',json={'email':EMAIL,'password':OLD}).status_code == 401
    login = client.post('/auth/login',json={'email':EMAIL,'password':NEW})
    assert login.status_code == 200
    recovered=client.post(f'/orders/{oid}/recover-pin-test',headers={
        'Authorization':'Bearer '+login.json()['access_token']},json={'password':NEW})
    assert recovered.status_code == 200 and recovered.json()['pin_test_only'] == order.json()['pin_test_only']
    assert client.get(f'/orders/{oid}/purchase-record',headers={
        'Authorization':'Bearer '+login.json()['access_token']}).json() == record
    with psycopg.connect(**parameters) as con:
        assert con.execute('SELECT id,status,total_grosze,pin_hash FROM orders').fetchall() == before
        assert con.execute('SELECT count(*) FROM password_reset_tokens').fetchone()[0] == 0


def test_native_reset_concurrent_issuance_budget_survives_restart(pg_reset_api):
    import json, psycopg
    from tests.test_password_reset_http import register as reset_register, EMAIL, NEW
    client, parameters = pg_reset_api
    reset_register(client)
    def issue(_):return client.post('/auth/password-reset-test/request',json={'email':EMAIL})
    with ThreadPoolExecutor(max_workers=8) as pool:responses=list(pool.map(issue, range(8)))
    assert all(r.status_code == 202 and r.json()==responses[0].json() for r in responses)
    files = list(pg_reset_api.reset_outbox.glob('*.json'))
    assert len(files) == 3
    with psycopg.connect(**parameters) as con:
        assert con.execute('SELECT count(*) FROM password_reset_tokens').fetchone()[0] == 3
        assert con.execute('SELECT attempts FROM password_reset_limits WHERE bucket=%s',
                           ('issue:'+hashlib.sha256(EMAIL.encode()).hexdigest(),)).fetchone()[0] == 3
    pg_reset_api.restart()
    assert issue(None).status_code == 202
    assert len(list(pg_reset_api.reset_outbox.glob('*.json'))) == 3
    tokens = [json.loads(p.read_text())['fragment'].split('=',1)[1] for p in files]
    def consume(token):return client.post('/auth/password-reset-test/confirm',
        json={'token':token,'new_password':NEW}).status_code
    with ThreadPoolExecutor(max_workers=3) as pool:assert sorted(pool.map(consume,tokens)) == [200,400,400]


def test_native_reset_serializes_old_password_login(pg_reset_api):
    from tests.test_password_reset_http import register as reset_register, request, confirm, EMAIL, OLD, NEW
    client, _ = pg_reset_api
    reset_register(client)
    token,_ = request(client, pg_reset_api.reset_outbox)
    def race(kind):
        return confirm(client,token) if kind=='reset' else client.post('/auth/login',json={'email':EMAIL,'password':OLD})
    with ThreadPoolExecutor(max_workers=2) as pool:reset,login=list(pool.map(race, ('reset','login')))
    assert reset.status_code == 200 and login.status_code in (200,401)
    if login.status_code == 200:
        assert client.get('/auth/me',headers={'Authorization':'Bearer '+login.json()['access_token']}).status_code == 401
    assert client.post('/auth/login',json={'email':EMAIL,'password':NEW}).status_code == 200


def test_native_reset_serializes_authenticated_password_change(pg_reset_api):
    from tests.test_password_reset_http import register as reset_register, request, confirm, OLD
    client, _ = pg_reset_api
    buyer=reset_register(client)
    token,_=request(client, pg_reset_api.reset_outbox)
    def race(kind):
        if kind=='reset':return confirm(client,token)
        return client.post('/auth/change-password',headers=buyer,
                           json={'current_password':OLD,'new_password':'Other-new-synthetic-password!'})
    with ThreadPoolExecutor(max_workers=2) as pool:reset,changed=list(pool.map(race, ('reset','change')))
    assert (reset.status_code,changed.status_code) in ((200,401),(400,200))
    assert client.get('/auth/me',headers=buyer).status_code == 401


def test_native_reset_database_failure_rolls_back_password_and_sessions(pg_reset_api):
    import psycopg
    from psycopg.conninfo import conninfo_to_dict
    from tests.test_password_reset_http import register as reset_register, request, confirm, EMAIL, OLD
    client, parameters = pg_reset_api
    buyer=reset_register(client)
    token,_=request(client,pg_reset_api.reset_outbox)
    admin = {**conninfo_to_dict(os.environ['WP_TEST_POSTGRES_DSN']), 'dbname':parameters['dbname']}
    with psycopg.connect(**admin,autocommit=True) as con:
        con.execute("CREATE FUNCTION fail_test_reset_revoke() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'test reset rollback'; END $$")
        con.execute('CREATE TRIGGER fail_test_reset_revoke BEFORE DELETE ON sessions FOR EACH ROW EXECUTE FUNCTION fail_test_reset_revoke()')
        try:
            assert confirm(client,token).status_code == 500
            assert con.execute('SELECT count(*) FROM sessions').fetchone()[0] == 1
            assert con.execute('SELECT count(*) FROM password_reset_tokens').fetchone()[0] == 1
            from argon2 import PasswordHasher
            assert PasswordHasher().verify(con.execute('SELECT password_hash FROM users').fetchone()[0],OLD)
        finally:
            con.execute('DROP TRIGGER fail_test_reset_revoke ON sessions')
            con.execute('DROP FUNCTION fail_test_reset_revoke()')
    # Uvicorn closes the connection after an unhandled 500. Validate recovery
    # through a fresh TCP connection rather than racing that socket's closure.
    with httpx.Client(base_url=str(client.base_url),trust_env=False,timeout=15) as recovered:
        assert recovered.get('/auth/me',headers=buyer).status_code == 200
        assert recovered.post('/auth/login',json={'email':EMAIL,'password':OLD}).status_code == 200
        assert confirm(recovered,token).status_code == 200


def test_native_reset_mail_queue_storage_constraints_only(pg_api):
    """Provisioning proof, not a claim that the SQLite worker supports PostgreSQL."""
    import psycopg
    client,parameters=pg_api
    _,uid=register(client,'klient')
    job=uuid4().hex
    with psycopg.connect(**parameters) as con:
        con.execute('''INSERT INTO reset_mail_queue
            (id,user_id,token_hash,event,key_id,payload,created_at,expires_at,state,available_at)
            VALUES(%s,%s,%s,'password_reset','synthetic-key',%s,1000,1900,'queued',1000)''',
            (job,uid,uuid4().hex,b'synthetic-encrypted-payload'))
        payload,user_type,payload_type=con.execute('''SELECT payload,pg_typeof(user_id)::text,
            pg_typeof(payload)::text FROM reset_mail_queue WHERE id=%s''',(job,)).fetchone()
        assert bytes(payload)==b'synthetic-encrypted-payload' and (user_type,payload_type)==('bigint','bytea')
        for mutation in ("state='accepted'", "state='leased'", "attempts=4",
                         "event='pickup_pin'", "expires_at=1000", "user_id=-999999"):
            with pytest.raises(psycopg.IntegrityError):
                with con.transaction():
                    con.execute('UPDATE reset_mail_queue SET '+mutation+' WHERE id=%s',(job,))
        con.execute("""UPDATE reset_mail_queue SET state='accepted',payload=NULL,result='ACCEPTED'
            WHERE id=%s""",(job,))
        assert con.execute('SELECT state,payload FROM reset_mail_queue WHERE id=%s',(job,)).fetchone()==('accepted',None)
        con.execute('DELETE FROM reset_mail_queue WHERE id=%s',(job,))

import json
import uuid
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from backend import app as module
from backend import address_delivery as delivery
from backend.checkout_vault import unb64


@pytest.fixture(scope='module')
def actors():
    patch = pytest.MonkeyPatch()
    patch.setenv('WP_ENABLE_ADDRESS_DELIVERY', '1')
    patch.setenv('WP_ENABLE_TEST_PAYMENTS', '1')
    with module.db() as con:
        con.executescript(delivery.SCHEMA_SQLITE)
    client = TestClient(module.app)
    users = []
    for role in ('rolnik', 'rolnik', 'klient', 'klient', 'dostawca'):
        data = {'email': uuid.uuid4().hex+'@example.invalid', 'password': 'PrivateTestPassword2026', 'role': role}
        response = client.post('/auth/register', json=data)
        assert response.status_code == 201, response.text
        token = client.post('/auth/login', json=data).json()['access_token']
        users.append(({'Authorization': 'Bearer '+token}, response.json()['id']))
    yield client, users
    patch.undo()


def new_product(client, farmer):
    response = client.post('/products', headers=farmer, json={
        'name': 'Towar do domu', 'stock': 10, 'price_grosze': 200, 'delivery_grosze': 500})
    assert response.status_code == 201, response.text
    return response.json()['id']


def setup(actors):
    client, users = actors
    farmer, other_farmer, buyer, other_buyer, courier = users
    day = datetime.now(ZoneInfo('Europe/Warsaw')).date()+timedelta(days=7)
    window = client.post('/address-delivery/windows', headers=farmer[0], json={
        'city': 'Legnica', 'postal_code': '59-220', 'weekday': day.weekday(), 'from_time': '10:00', 'to_time': '16:00'})
    assert window.status_code == 200, window.text
    pid = new_product(client, farmer[0])
    body = {'product_id': pid, 'quantity': 2, 'fulfillment': 'dostawa',
            'delivery_city': 'Legnica', 'delivery_street': 'Testowa 1', 'delivery_postal_code': '59-220',
            'address_delivery': {'window_id': window.json()['id'], 'delivery_date': day.isoformat(),
                                 'available_from': '12:00', 'available_to': '18:00', 'phone': '+48 500 100 200'}}
    return client, users, pid, body


def create(actors):
    client, users, pid, body = setup(actors)
    response = client.post('/orders', headers=users[2][0], json=body)
    assert response.status_code == 201, response.text
    return client, users, pid, body, response.json()['id']


def decide(client, farmer, oid, decision, revision=0):
    return client.post(f'/address-delivery/requests/{oid}/decision', headers=farmer,
                       json={'decision': decision, 'revision': revision})


def stock(pid):
    with module.db() as con:
        return con.execute('SELECT stock FROM products WHERE id=?', (pid,)).fetchone()['stock']


def test_windows_and_requests_are_scoped_and_phone_is_encrypted(actors):
    client, users, pid, body, oid = create(actors)
    with module.db() as con:
        row = con.execute('SELECT * FROM address_delivery_requests WHERE order_id=?', (oid,)).fetchone()
        assert row['agreed_from'] == 720 and row['agreed_to'] == 960
        assert '500100200' not in row['phone_sealed']
        envelope = json.loads(row['phone_sealed'])
        clear = AESGCM(module.CHECKOUT_VAULT.keys[envelope['key_id']]).decrypt(
            unb64(envelope['nonce']), unb64(envelope['ciphertext']), f'wp.delivery.phone.v1:{oid}:{users[2][1]}'.encode())
        assert clear == b'+48500100200'
    farmer_list = client.get('/address-delivery/requests/mine', headers=users[0][0]).json()['items']
    assert any(r['order_id'] == oid for r in farmer_list)
    assert 'phone' not in json.dumps(farmer_list) and '500100200' not in json.dumps(farmer_list)
    assert not any(r['order_id'] == oid for r in client.get('/address-delivery/requests/mine', headers=users[3][0]).json()['items'])
    assert client.get('/address-delivery/requests/mine', headers=users[4][0]).status_code == 403
    assert decide(client, users[1][0], oid, 'accepted').status_code == 404
    assert decide(client, users[2][0], oid, 'accepted').status_code == 403


def test_acceptance_blocks_payment_and_dispatch_until_seller_accepts(actors):
    client, users, pid, body, oid = create(actors)
    assert client.post(f'/orders/{oid}/assign-courier-test', headers=users[0][0], json={'courier_id': users[4][1]}).status_code == 200
    event = {'event_id': uuid.uuid4().hex, 'event_type': 'payment_success_test'}
    assert client.post(f'/test/payments/{oid}/events', headers=users[2][0], json=event).status_code == 409
    assert client.post(f'/orders/{oid}/dispatch-test', headers=users[0][0]).status_code == 409
    assert decide(client, users[0][0], oid, 'accepted').status_code == 200
    assert decide(client, users[0][0], oid, 'accepted').json()['already_processed'] is True
    assert decide(client, users[0][0], oid, 'declined').status_code == 409
    assert client.post(f'/test/payments/{oid}/events', headers=users[2][0], json=event).status_code == 200
    assert client.post(f'/orders/{oid}/dispatch-test', headers=users[0][0]).status_code == 200
    assert stock(pid) == 8


def test_decline_restores_stock_once_and_releases_hold(actors):
    client, users, pid, body, oid = create(actors)
    assert decide(client, users[0][0], oid, 'declined').status_code == 200
    assert decide(client, users[0][0], oid, 'declined').json()['already_processed'] is True
    assert client.post(f'/orders/{oid}/cancel-test', headers=users[2][0]).status_code == 409
    assert stock(pid) == 10
    with module.db() as con:
        assert con.execute('SELECT released_at FROM inventory_reservations WHERE order_id=?', (oid,)).fetchone()['released_at']


@pytest.mark.parametrize('decision', ['accepted', 'declined'])
def test_whole_shipment_has_one_atomic_decision(actors, decision):
    client, users, pid, body = setup(actors)
    pid2 = new_product(client, users[0][0])
    client.delete('/cart/items', headers=users[2][0])
    for item in (pid, pid2):
        assert client.put('/cart/items', headers=users[2][0], json={'product_id': item, 'quantity': 2}).status_code == 200
    cart = {k: v for k, v in body.items() if k not in ('product_id', 'quantity')}
    cart['farmer_id'] = users[0][1]
    response = client.post('/cart/checkout-test', headers=users[2][0], json=cart)
    assert response.status_code == 201, response.text
    ids = [o['id'] for o in response.json()['orders']]
    assert len(ids) == 2
    assert decide(client, users[0][0], ids[0], decision).status_code == 200
    with module.db() as con:
        assert all(con.execute('SELECT state FROM address_delivery_requests WHERE order_id=?', (oid,)).fetchone()['state'] == decision for oid in ids)
    assert [stock(i) for i in (pid, pid2)] == ([10, 10] if decision == 'declined' else [8, 8])


def test_invalid_missing_and_inactive_windows_do_not_reserve_goods(actors):
    client, users, pid, body = setup(actors)
    for change in ({'available_from': '18:00', 'available_to': '19:00'},
                   {'phone': 'abcdefghi'}, {'delivery_date': '2026-02-30'}):
        altered = {**body, 'address_delivery': {**body['address_delivery'], **change}}
        assert client.post('/orders', headers=users[2][0], json=altered).status_code == 422
    assert client.post('/orders', headers=users[2][0], json={**body, 'delivery_city': 'Inne miasto'}).status_code == 422
    assert client.post('/orders', headers=users[2][0], json={**body, 'delivery_postal_code': '00-001'}).status_code == 422
    assert client.post('/orders', headers=users[2][0], json={k: v for k, v in body.items() if k != 'address_delivery'}).status_code == 422
    assert client.patch('/address-delivery/windows/'+body['address_delivery']['window_id'], headers=users[0][0], json={'active': False}).status_code == 200
    assert client.post('/orders', headers=users[2][0], json=body).status_code == 422
    assert stock(pid) == 10


def test_legacy_idempotency_payload_is_compatible_after_enabling_feature(actors, monkeypatch):
    client, users, pid, body = setup(actors)
    body.pop('address_delivery')
    headers = {**users[2][0], 'Idempotency-Key': uuid.uuid4().hex}
    with monkeypatch.context() as patch:
        patch.setenv('WP_ENABLE_ADDRESS_DELIVERY', '0')
        original = client.post('/orders', headers=headers, json=body)
    assert original.status_code == 201, original.text
    retry = client.post('/orders', headers=headers, json=body)
    assert retry.status_code == 201 and retry.json() == original.json()
    assert stock(pid) == 8


def test_cannot_disable_feature_with_active_requests(actors, monkeypatch):
    create(actors)
    with monkeypatch.context() as patch:
        patch.setenv('WP_ENABLE_ADDRESS_DELIVERY', '0')
        with pytest.raises(RuntimeError, match='Nie można wyłączyć akceptacji'):
            with TestClient(module.app):
                pass


def test_seller_settings_are_owned_and_disabling_window_keeps_booked_terms(actors):
    client, users, pid, body, oid = create(actors)
    url = '/address-delivery/windows/'+body['address_delivery']['window_id']
    assert client.get('/address-delivery/windows/mine', headers=users[2][0]).status_code == 403
    assert client.patch(url, headers=users[1][0], json={'active': False}).status_code == 404
    assert client.patch(url, headers=users[0][0], json={'active': False}).status_code == 200
    assert decide(client, users[0][0], oid, 'accepted').status_code == 200
    with module.db() as con:
        row = con.execute('SELECT agreed_from,agreed_to FROM address_delivery_requests WHERE order_id=?', (oid,)).fetchone()
        assert (row['agreed_from'], row['agreed_to']) == (720, 960)


def test_expired_request_cannot_be_accepted_or_restore_stock_twice(actors):
    client, users, pid, body, oid = create(actors)
    from datetime import timezone
    with module.db() as con:
        con.execute('UPDATE inventory_reservations SET expires_at=? WHERE order_id=?',
                    ((datetime.now(timezone.utc)-timedelta(minutes=1)).isoformat(), oid))
    assert decide(client, users[0][0], oid, 'accepted').status_code == 409
    module.run_reservation_expiry()
    module.run_reservation_expiry()
    assert stock(pid) == 10


def test_changed_contact_cannot_replay_same_order_key(actors):
    client, users, pid, body = setup(actors)
    headers = {**users[2][0], 'Idempotency-Key': uuid.uuid4().hex}
    original = client.post('/orders', headers=headers, json=body)
    assert original.status_code == 201
    changed = {**body, 'address_delivery': {**body['address_delivery'], 'phone': '+48 500 100 201'}}
    assert client.post('/orders', headers=headers, json=changed).status_code == 409
    assert stock(pid) == 8

"""Persisted hash corruption must not bypass authentication or PIN limits."""
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from backend import app as api
from tests.test_purchase_records import purchase


@pytest.mark.parametrize('stored_hash', ['', 'invalid-hash', '$argon2id$broken'])
def test_invalid_password_hash_counts_failures_without_creating_session(stored_hash):
    client = TestClient(api.app, raise_server_exceptions=False)
    email = f'{uuid4().hex}@example.invalid'
    with api.db() as con:
        uid = con.execute('INSERT INTO users(email,password_hash,role) VALUES(?,?,?)',
                          (email, stored_hash, 'klient')).lastrowid
    for _ in range(5):
        response = client.post('/auth/login', json={'email': email, 'password': 'Synthetic-password-123'})
        assert response.status_code == 401
        if stored_hash:
            assert stored_hash not in response.text
    assert client.post('/auth/login', json={'email': email, 'password': 'Synthetic-password-123'}).status_code == 429
    with api.db() as con:
        assert con.execute('SELECT failures FROM login_attempts WHERE email=?', (email,)).fetchone()[0] == 5
        assert con.execute('SELECT COUNT(*) FROM sessions WHERE user_id=?', (uid,)).fetchone()[0] == 0
        assert con.execute('SELECT password_hash FROM users WHERE id=?', (uid,)).fetchone()[0] == stored_hash


@pytest.mark.parametrize('cart', [False, True])
@pytest.mark.parametrize('stored_hash', ['', 'invalid-hash', '$argon2id$broken', 'different-valid-pin'])
def test_every_order_hash_must_verify_and_failures_lock_whole_shipment(cart, stored_hash):
    client, farmer, buyer, products, point, point_body, receipt, ids, *_ = purchase(cart=cart)
    pin = receipt['shipment_pin_test_only'] if cart else receipt['pin_test_only']
    if stored_hash == 'different-valid-pin':
        stored_hash = api.ph.hash('000001' if pin != '000001' else '000002')
    # Synthetic state setup; preserve every other purchase field and the original PIN.
    with api.db() as con:
        for oid in ids:
            con.execute("UPDATE orders SET status='gotowe_do_odbioru_testowo' WHERE id=?", (oid,))
        con.execute('UPDATE orders SET pin_hash=? WHERE id=?', (stored_hash, ids[-1]))
    url = f'/shipments/{receipt["shipment_id"]}/confirm' if cart else f'/orders/{ids[0]}/confirm'
    for remaining in range(4, -1, -1):
        response = client.post(url, headers=farmer, json={'pin': pin, 'checked_goods': True})
        assert response.status_code == 200
        assert response.json() == {'confirmed': False, 'remaining_attempts': remaining}
    assert client.post(url, headers=farmer, json={'pin': pin, 'checked_goods': True}).status_code == 409
    with api.db() as con:
        for oid in ids:
            row = con.execute('SELECT * FROM orders WHERE id=?', (oid,)).fetchone()
            assert row['pin_attempts'] == 5 and row['pin_used'] == 0
            assert row['status'] == 'gotowe_do_odbioru_testowo' and row['confirmed_at'] is None
        assert con.execute('SELECT pin_hash FROM orders WHERE id=?', (ids[-1],)).fetchone()[0] == stored_hash


def test_remaining_attempts_reflect_most_restricted_order():
    client, farmer, buyer, products, point, point_body, receipt, ids, *_ = purchase(cart=True)
    with api.db() as con:
        for oid in ids:
            con.execute("UPDATE orders SET status='gotowe_do_odbioru_testowo' WHERE id=?", (oid,))
        con.execute('UPDATE orders SET pin_attempts=4 WHERE id=?', (ids[-1],))
    pin = receipt['shipment_pin_test_only']
    wrong = '000001' if pin != '000001' else '000002'
    response = client.post(f'/shipments/{receipt["shipment_id"]}/confirm', headers=farmer,
                           json={'pin': wrong, 'checked_goods': True})
    assert response.json() == {'confirmed': False, 'remaining_attempts': 0}


def test_same_pin_with_independently_salted_hashes_confirms_all_orders():
    client, farmer, buyer, products, point, point_body, receipt, ids, *_ = purchase(cart=True)
    pin = receipt['shipment_pin_test_only']
    with api.db() as con:
        for oid in ids:
            con.execute("UPDATE orders SET status='gotowe_do_odbioru_testowo',pin_hash=? WHERE id=?",
                        (api.ph.hash(pin), oid))
    response = client.post(f'/shipments/{receipt["shipment_id"]}/confirm', headers=farmer,
                           json={'pin': pin, 'checked_goods': True})
    assert response.status_code == 200 and response.json()['confirmed'] is True
    assert response.json()['confirmed_orders'] == len(ids)
    with api.db() as con:
        for oid in ids:
            row = con.execute('SELECT * FROM orders WHERE id=?', (oid,)).fetchone()
            assert row['pin_used'] == 1 and row['status'] == 'odebrane'
            assert row['confirmed_at'] is not None and row['pin_attempts'] == 0

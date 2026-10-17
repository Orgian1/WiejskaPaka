"""Restore drills use only disposable databases and synthetic HTTP purchases."""
from contextlib import closing
import hashlib
from pathlib import Path
import sqlite3
from uuid import uuid4

import pytest

from backend.checkout_vault import create_ring
from backend.payment_integrity import audit_payment_integrity
from tests.test_purchase_record_http_restart import server, setup


def online_copy(source, target):
    # This helper is a rehearsal, not a user-facing backup/overwrite command.
    assert not target.exists()
    with closing(sqlite3.connect(source.resolve().as_uri()+'?mode=ro', uri=True)) as src:
        with closing(sqlite3.connect(target)) as dst:
            src.backup(dst)
            assert dst.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
            assert dst.execute('PRAGMA foreign_key_check').fetchall() == []


def key_path(database):
    return Path(str(database)+'.checkout-key')


def copy_key(source, target):
    # Fresh test-only destination; retain restrictive permissions on POSIX.
    with key_path(target).open('xb') as stream:
        key_path(target).chmod(0o600)
        stream.write(key_path(source).read_bytes())


def purchase(client):
    farmer, buyer, products = setup(client)
    for product in products:
        assert client.put('/cart/items', headers=buyer,
                          json={'product_id': product, 'quantity': 1}).status_code == 200
    body = {'fulfillment': 'dostawa', 'delivery_city': 'Test',
            'delivery_street': 'Syntetyczna 1', 'delivery_postal_code': '45-001'}
    headers = {**buyer, 'Idempotency-Key': uuid4().hex}
    response = client.post('/cart/checkout-test', headers=headers, json=body)
    assert response.status_code == 201
    receipt = response.json()
    for order in receipt['orders']:
        assert client.post(f'/test/payments/{order["id"]}/events', headers=buyer,
            json={'event_id': uuid4().hex, 'event_type': 'payment_success_test'}).status_code == 200
    url = f'/shipments/{receipt["shipment_id"]}/purchase-record'
    record = client.get(url, headers=buyer)
    assert record.status_code == 200
    return farmer, buyer, products, headers, body, receipt, url, record.json()


def test_online_wal_snapshot_restores_paid_purchase_without_duplicate(tmp_path):
    source = tmp_path/'source.sqlite3'
    restored = tmp_path/'restored # 100%.sqlite3'
    with closing(sqlite3.connect(source)) as con:
        assert con.execute('PRAGMA journal_mode=WAL').fetchone()[0] == 'wal'
    with closing(sqlite3.connect(source)) as keeper, server(source) as client:
        # Hold an open WAL connection before the purchase so closing individual
        # HTTP connections cannot checkpoint it as the last connection.
        assert keeper.execute('PRAGMA journal_mode').fetchone()[0] == 'wal'
        farmer, buyer, products, headers, body, receipt, url, record = purchase(client)
        original_key = key_path(source).read_bytes()
        # Keep a writer open: the backup must include committed WAL pages and
        # exclude a second connection's uncommitted product edit.
        with closing(sqlite3.connect(source)) as writer:
            writer.execute('BEGIN IMMEDIATE')
            writer.execute('UPDATE products SET price_grosze=999999 WHERE id=?', (products[0],))
            assert Path(str(source)+'-wal').stat().st_size > 32
            online_copy(source, restored)
            copy_key(source, restored)
            writer.rollback()
        assert key_path(source).read_bytes() == original_key
        assert client.get(url, headers=buyer).json() == record
    with closing(sqlite3.connect(restored)) as con:
        con.row_factory = sqlite3.Row
        assert con.execute('SELECT price_grosze FROM products WHERE id=?', (products[0],)).fetchone()[0] == 199
        assert con.execute('SELECT COUNT(*) FROM orders').fetchone()[0] == 2
        assert con.execute('SELECT SUM(delivery_grosze), SUM(total_grosze) FROM orders').fetchone()[:] == (501, 1001)
        assert audit_payment_integrity(con) == {'checked_payments': 2, 'issues': [], 'ok': True}
    with server(restored) as client:
        assert client.get(url, headers=buyer).json() == record
        replay = client.post('/cart/checkout-test', headers=headers, json=body)
        assert replay.status_code == 201 and replay.json() == receipt
        assert replay.headers['cache-control'] == 'no-store'
        assert client.get(url, headers=farmer).json() == record
        # Logout in the restored copy must not mutate the source session.
        assert client.post('/auth/logout', headers=buyer).status_code == 200
        assert client.get(url, headers=buyer).status_code == 401
    with server(source) as client:
        assert client.get(url, headers=buyer).status_code == 200
    with closing(sqlite3.connect(restored)) as con:
        assert con.execute('SELECT COUNT(*) FROM orders').fetchone()[0] == 2
        assert con.execute('SELECT COUNT(*) FROM checkout_idempotency').fetchone()[0] == 1
        assert con.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'


@pytest.mark.parametrize('problem', ['missing', 'wrong'])
def test_restored_ciphertext_refuses_missing_or_wrong_key_without_replacement(tmp_path, problem):
    source, restored = tmp_path/'source.sqlite3', tmp_path/'restore.sqlite3'
    with server(source) as client:
        purchase(client)
    online_copy(source, restored)
    original_source = hashlib.sha256(source.read_bytes()).digest()
    original_key = key_path(source).read_bytes()
    if problem == 'wrong':
        create_ring(key_path(restored))
    expected_key = key_path(restored).read_bytes() if key_path(restored).exists() else None
    before = hashlib.sha256(restored.read_bytes()).digest()
    with pytest.raises(AssertionError, match='Disposable server exited'):
        with server(restored):
            pytest.fail('Restored database started without the correct key')
    assert hashlib.sha256(restored.read_bytes()).digest() == before
    assert (key_path(restored).read_bytes() if key_path(restored).exists() else None) == expected_key
    assert hashlib.sha256(source.read_bytes()).digest() == original_source
    assert key_path(source).read_bytes() == original_key


def test_backup_preserves_immutable_purchase_record_guards(tmp_path):
    source, restored = tmp_path/'source.sqlite3', tmp_path/'restore.sqlite3'
    with server(source) as client:
        purchase(client)
    online_copy(source, restored)
    with closing(sqlite3.connect(restored)) as con:
        before = con.execute('SELECT * FROM order_purchase_records ORDER BY order_id').fetchall()
        for sql in ('DELETE FROM order_purchase_records',
                    'UPDATE order_purchase_records SET product_name=product_name'):
            with pytest.raises(sqlite3.IntegrityError):
                con.execute(sql)
            con.rollback()
        assert con.execute('SELECT * FROM order_purchase_records ORDER BY order_id').fetchall() == before


def test_restore_rolls_back_logout_and_offline_session_invalidation_preserves_orders(tmp_path):
    source, restored = tmp_path/'source.sqlite3', tmp_path/'restore.sqlite3'
    with server(source) as client:
        _, buyer, _, _, _, _, url, record = purchase(client)
        online_copy(source, restored)
        copy_key(source, restored)
        assert client.post('/auth/logout', headers=buyer).status_code == 200
        assert client.get(url, headers=buyer).status_code == 401
    # Recovery restores database state as of the snapshot, including sessions.
    # Demonstrate this limitation rather than claiming backup is a security log.
    with server(restored) as client:
        assert client.get(url, headers=buyer).json() == record
    with closing(sqlite3.connect(restored)) as con, con:
        before = con.execute('SELECT * FROM order_purchase_records ORDER BY order_id').fetchall()
        # Only the newly created disposable restore is modified; never the source.
        con.execute('DELETE FROM sessions')
    with server(restored) as client:
        assert client.get(url, headers=buyer).status_code == 401
    with closing(sqlite3.connect(restored)) as con:
        con.row_factory = sqlite3.Row
        assert con.execute('SELECT COUNT(*) FROM orders').fetchone()[0] == 2
        assert [tuple(row) for row in con.execute('SELECT * FROM order_purchase_records ORDER BY order_id')] == before
        assert audit_payment_integrity(con)['ok'] is True

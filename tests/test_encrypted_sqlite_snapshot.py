"""Encrypted recovery preserves purchases and rejects unauthenticated input."""
from contextlib import closing
import os
import sqlite3
import struct

import pytest
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from backend.checkout_vault import read_ring
import scripts.encrypted_sqlite_snapshot as operation
from tests.test_sqlite_recovery_rehearsal import purchase, key_path
from tests.test_purchase_record_http_restart import server


def paths(tmp_path):
    keys, archives = tmp_path/'keys', tmp_path/'archives'
    keys.mkdir(); archives.mkdir()
    key, archive = keys/'master.backup-key', archives/'copy.wpbackup'
    operation.make_backup_key(key)
    return key, archive


def test_encrypted_purchase_roundtrip_revokes_sessions_and_preserves_source(tmp_path):
    key, archive = paths(tmp_path)
    source = tmp_path/'source.sqlite3'
    with server(source) as client:
        _, buyer, _, _, _, _, url, _ = purchase(client)
        result = operation.encrypted_backup(source, key_path(source), key, archive)
        assert result['orders'] == result['payments_checked'] == 2
        assert result['encrypted_backup']
    before = source.read_bytes(), key_path(source).read_bytes(), key.read_bytes()
    assert b'SQLite format 3' not in archive.read_bytes()
    restored = tmp_path/'restored'
    result = operation.encrypted_restore(archive, key, restored)
    assert result['revoked_sessions'] == 2 and result['payments_checked'] == 2
    with server(restored/'database.sqlite3') as client:
        assert client.get(url, headers=buyer).status_code == 401
    with closing(sqlite3.connect(restored/'database.sqlite3')) as con:
        assert con.execute('SELECT COUNT(*) FROM order_purchase_records').fetchone()[0] == 2
        assert con.execute('SELECT SUM(delivery_grosze) FROM orders').fetchone()[0] == 501
    assert before == (source.read_bytes(), key_path(source).read_bytes(), key.read_bytes())
    with pytest.raises(FileExistsError):
        operation.encrypted_restore(archive, key, restored)
    if os.name == 'posix':
        assert archive.stat().st_mode & 0o077 == key.stat().st_mode & 0o077 == 0
    assert not list(tmp_path.glob('.wp-*'))
    assert not list(archive.parent.glob('.wp-*'))


@pytest.mark.parametrize('damage', ['magic', 'key_id', 'nonce', 'ciphertext', 'tag', 'truncate', 'append', 'wrong_key'])
def test_authentication_failure_never_stages_plaintext(tmp_path, monkeypatch, damage):
    key, archive = paths(tmp_path)
    active, keys = read_ring(key)
    header = operation.MAGIC + active.encode() + bytes(12)
    data = bytearray(header + AESGCM(keys[active]).encrypt(bytes(12), b'private payload'*10, header))
    offsets = {'magic':0, 'key_id':8, 'nonce':32, 'ciphertext':44, 'tag':-1}
    if damage in offsets:
        data[offsets[damage]] ^= 1
    elif damage == 'truncate':
        data = data[:-1]
    elif damage == 'append':
        data += b'x'
    else:
        key = key.parent/'other.backup-key'
        operation.make_backup_key(key)
    archive.write_bytes(data)
    def forbidden(*args, **kwargs):
        pytest.fail('Unauthenticated content reached plaintext staging')
    monkeypatch.setattr(operation.tempfile, 'TemporaryDirectory', forbidden)
    with pytest.raises(ValueError):
        operation.encrypted_restore(archive, key, tmp_path/'restore')
    assert not (tmp_path/'restore').exists()


@pytest.mark.parametrize('payload', [b'invalid', operation.INNER + struct.pack('>QI', 0, 1) + b'x',
    operation.INNER + struct.pack('>QI', operation.MAX_DATABASE_BYTES+1, 1),
    operation.INNER + struct.pack('>QI', 1, 1) + b'x'])
def test_authenticated_malformed_content_creates_no_destination(tmp_path, payload):
    key, archive = paths(tmp_path)
    active, keys = read_ring(key)
    header = operation.MAGIC + active.encode() + bytes(12)
    archive.write_bytes(header + AESGCM(keys[active]).encrypt(bytes(12), payload, header))
    with pytest.raises(ValueError):
        operation.encrypted_restore(archive, key, tmp_path/'restore')
    assert not (tmp_path/'restore').exists()
    assert not list(tmp_path.glob('.wp-*'))


def test_key_separation_and_no_overwrite(tmp_path):
    key, archive = paths(tmp_path)
    before = key.read_bytes()
    with pytest.raises(FileExistsError):
        operation.make_backup_key(key)
    assert key.read_bytes() == before
    same_folder = archive.parent/'bad.backup-key'
    operation.make_backup_key(same_folder)
    with pytest.raises(ValueError):
        operation.encrypted_restore(archive, same_folder, tmp_path/'restore')
    with pytest.raises(ValueError):
        operation.encrypted_backup(tmp_path/'missing', key, key, archive)
    archive.write_bytes(b'existing')
    with pytest.raises(FileExistsError):
        operation._publish(archive, b'replacement')
    assert archive.read_bytes() == b'existing'
    assert not list(archive.parent.glob('.wp-*'))


def test_bounded_input_and_cli_privacy(tmp_path, capsys):
    key, archive = paths(tmp_path)
    archive.write_bytes(b'x'*100)
    with pytest.raises(ValueError):
        operation._read_regular(archive, 99)
    assert operation.main(['restore', '--archive', str(archive), '--backup-key', str(key),
                           '--destination', str(tmp_path/'private@example.invalid')]) == 1
    output = capsys.readouterr()
    assert not output.out and str(tmp_path) not in output.err


def test_cli_key_creation_is_private_and_non_destructive(tmp_path, capsys):
    key = tmp_path/'private.backup-key'
    assert operation.main(['init-key', '--backup-key', str(key)]) == 0
    assert capsys.readouterr().out.strip() == '{"created": true}'
    before = key.read_bytes()
    assert operation.main(['init-key', '--backup-key', str(key)]) == 1
    assert key.read_bytes() == before
    assert str(key) not in capsys.readouterr().err

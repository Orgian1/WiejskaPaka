"""Operator recovery must preserve purchases without resurrecting sessions."""
from contextlib import closing
import hashlib
import os
import sqlite3

import pytest

from backend.checkout_vault import create_ring
from scripts.sqlite_snapshot import snapshot, main
from tests.test_sqlite_recovery_rehearsal import purchase, key_path
from tests.test_purchase_record_http_restart import server


def test_backup_restore_preserves_purchase_revokes_sessions_and_never_overwrites(tmp_path):
    source = tmp_path / 'source.sqlite3'
    backup, restored = tmp_path / 'backup', tmp_path / 'restored'
    with server(source) as client:
        _, buyer, _, _, _, _, url, record = purchase(client)
        result = snapshot(source, key_path(source), backup)
        assert result['orders'] == 2 and result['payments_checked'] == 2
        assert not result['restored'] and not result['encrypted_backup']
        assert client.get(url, headers=buyer).status_code == 200
    source_hash = hashlib.sha256(source.read_bytes()).digest()
    result = snapshot(backup/'database.sqlite3', backup/'database.sqlite3.checkout-key',
                      restored, restore=True)
    assert result['revoked_sessions'] == 2
    with server(restored/'database.sqlite3') as client:
        assert client.get(url, headers=buyer).status_code == 401
    with closing(sqlite3.connect(restored/'database.sqlite3')) as con:
        assert con.execute('SELECT COUNT(*) FROM order_purchase_records').fetchone()[0] == 2
        assert con.execute('SELECT SUM(delivery_grosze) FROM orders').fetchone()[0] == 501
    with pytest.raises(FileExistsError):
        snapshot(source, key_path(source), restored, restore=True)
    assert hashlib.sha256(source.read_bytes()).digest() == source_hash
    if os.name == 'posix':
        assert restored.stat().st_mode & 0o077 == 0
        for name in ('database.sqlite3', 'database.sqlite3.checkout-key'):
            assert (restored/name).stat().st_mode & 0o077 == 0


@pytest.mark.parametrize('problem', ['wrong_key', 'corrupt', 'missing', 'directory'])
def test_failed_snapshot_leaves_source_untouched_and_no_partial_destination(tmp_path, problem):
    source, target = tmp_path/'source.sqlite3', tmp_path/'copy'
    with server(source) as client:
        purchase(client)
    key = key_path(source)
    if problem == 'wrong_key':
        key = tmp_path/'foreign-key'
        create_ring(key)
    elif problem == 'corrupt':
        source.write_bytes(b'not a sqlite database')
    elif problem == 'missing':
        source.unlink()
    elif problem == 'directory':
        source = tmp_path
    before = source.read_bytes() if source.is_file() else None
    with pytest.raises((ValueError, sqlite3.Error, OSError)):
        snapshot(source, key, target, restore=True)
    assert not target.exists()
    if before is not None:
        assert source.read_bytes() == before


def test_cli_hides_private_paths_and_rejects_invalid_input(tmp_path, capsys):
    private = str(tmp_path/'private@example.invalid')
    assert main(['restore', '--source', private, '--key-file', private,
                 '--destination', str(tmp_path/'out')]) == 1
    output = capsys.readouterr()
    assert private not in output.err and not output.out


def test_online_copy_excludes_uncommitted_wal_write(tmp_path):
    source, target = tmp_path/'wal.sqlite3', tmp_path/'snapshot'
    with server(source) as client, closing(sqlite3.connect(source)) as writer:
        _, _, products, _, _, _, _, _ = purchase(client)
        writer.execute('PRAGMA journal_mode=WAL')
        writer.execute('BEGIN IMMEDIATE')
        writer.execute('UPDATE products SET price_grosze=999999 WHERE id=?', (products[0],))
        snapshot(source, key_path(source), target)
        writer.rollback()
    with closing(sqlite3.connect(target/'database.sqlite3')) as con:
        assert con.execute('SELECT price_grosze FROM products WHERE id=?', (products[0],)).fetchone()[0] == 199


@pytest.mark.parametrize('timeout', [0, -1, float('nan'), float('inf')])
def test_invalid_timeout_creates_no_files(tmp_path, timeout):
    with pytest.raises(ValueError):
        snapshot(tmp_path/'absent', tmp_path/'key', tmp_path/'out', timeout=timeout)
    assert list(tmp_path.iterdir()) == []


def test_snapshot_sync_uses_write_capable_regular_file_handles(tmp_path, monkeypatch):
    """Model Windows' write-handle requirement even when running on Linux."""
    import stat
    import scripts.sqlite_snapshot as operation
    source = tmp_path/'source.sqlite3'
    with server(source) as client:
        purchase(client)
    real_sync = os.fsync
    regular_synced = []
    def require_write_handle(fd):
        if stat.S_ISREG(os.fstat(fd).st_mode):
            # Zero bytes leave data unchanged, but a read-only fd must fail.
            os.write(fd, b'')
            regular_synced.append(fd)
        return real_sync(fd)
    monkeypatch.setattr(operation.os, 'fsync', require_write_handle)
    result = snapshot(source, key_path(source), tmp_path/'copy', restore=True)
    assert result['orders'] == 2 and len(regular_synced) >= 3

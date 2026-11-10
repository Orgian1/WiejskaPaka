"""Authenticated encrypted SQLite snapshots for bounded local test databases."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import secrets
import sqlite3
import stat
import struct
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from backend.checkout_vault import b64, canonical, read_ring, sync_directory
from scripts.sqlite_snapshot import snapshot

MAGIC = b'WPSNAP1\0'
INNER = b'WPDB001\0'
HEADER_SIZE = 44  # version (8), key identifier (24), random nonce (12)
MAX_DATABASE_BYTES = 64 * 1024 * 1024
MAX_KEY_BYTES = 16384
MAX_CONTAINER_BYTES = HEADER_SIZE + 16 + len(INNER) + 12 + MAX_DATABASE_BYTES + MAX_KEY_BYTES


def _read_regular(path, maximum):
    path = Path(path)
    if path.is_symlink():
        raise ValueError('Dowiązania nie są dozwolone')
    fd = os.open(path, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_NONBLOCK', 0))
    with os.fdopen(fd, 'rb') as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_size > maximum:
            raise ValueError('Nieprawidłowy rodzaj lub rozmiar pliku')
        data = stream.read(maximum + 1)
    if len(data) > maximum:
        raise ValueError('Przekroczono limit pliku')
    return data


def _write_private(path, data):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def _publish(destination, data):
    """Publish a complete file atomically; hard-link creation cannot overwrite."""
    destination = Path(destination)
    fd, name = tempfile.mkstemp(prefix='.wp-backup-', dir=destination.parent)
    temporary = Path(name)
    published = False
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, destination)
        published = True
        sync_directory(destination.parent)
    except BaseException:
        if published:
            destination.unlink()
        raise
    finally:
        temporary.unlink(missing_ok=True)


def make_backup_key(path):
    """New independent random key, never replacement of an existing key."""
    path = Path(path)
    if path.exists() or path.is_symlink():
        raise FileExistsError('Klucz już istnieje')
    key = secrets.token_bytes(32)
    kid = hashlib.sha256(key).hexdigest()[:24]
    _publish(path, canonical({'active': kid, 'keys': {kid: b64(key)}}))
    return {'created': True}


def _separate_key(archive, backup_key):
    # Logical separation only; separate disks/hosts/ACLs are an operator concern.
    if Path(backup_key).resolve().is_relative_to(Path(archive).parent.resolve()):
        raise ValueError('Klucz kopii musi być poza katalogiem archiwum')
    return read_ring(backup_key)


def encrypted_backup(source, checkout_key, backup_key, destination):
    destination = Path(destination)
    if destination.exists() or destination.is_symlink():
        raise FileExistsError('Kopia już istnieje')
    active, keys = _separate_key(destination, backup_key)
    _, live_keys = read_ring(checkout_key)
    if set(keys.values()) & set(live_keys.values()):
        raise ValueError('Wymagany niezależny klucz kopii')
    with tempfile.TemporaryDirectory(prefix='.wp-snapshot-', dir=destination.parent) as folder:
        stage = Path(folder)/'snapshot'
        result = snapshot(source, checkout_key, stage)
        database = _read_regular(stage/'database.sqlite3', MAX_DATABASE_BYTES)
        ring = _read_regular(stage/'database.sqlite3.checkout-key', MAX_KEY_BYTES)
        payload = INNER + struct.pack('>QI', len(database), len(ring)) + database + ring
        nonce = secrets.token_bytes(12)
        header = MAGIC + active.encode('ascii') + nonce
        encrypted = header + AESGCM(keys[active]).encrypt(nonce, payload, header)
        if read_ring(backup_key) != (active, keys):
            raise ValueError('Klucz kopii zmienił się podczas operacji')
        _publish(destination, encrypted)
    return {**result, 'encrypted_backup': True}


def encrypted_restore(archive, backup_key, destination):
    destination = Path(destination)
    if destination.exists() or destination.is_symlink():
        raise FileExistsError('Cel już istnieje')
    _, keys = _separate_key(archive, backup_key)
    encrypted = _read_regular(archive, MAX_CONTAINER_BYTES)
    if len(encrypted) < HEADER_SIZE + 16 + len(INNER) + 12 or encrypted[:8] != MAGIC:
        raise ValueError('Nieprawidłowy format kopii')
    header = encrypted[:HEADER_SIZE]
    try:
        key = keys[header[8:32].decode('ascii')]
        # AESGCM returns plaintext only after verifying the authentication tag.
        payload = AESGCM(key).decrypt(header[32:44], encrypted[HEADER_SIZE:], header)
    except (InvalidTag, KeyError, UnicodeError) as exc:
        raise ValueError('Nie można uwierzytelnić kopii') from exc
    if payload[:8] != INNER or len(payload) < 20:
        raise ValueError('Nieprawidłowa zawartość kopii')
    size, key_size = struct.unpack('>QI', payload[8:20])
    if not 0 < size <= MAX_DATABASE_BYTES or not 0 < key_size <= MAX_KEY_BYTES or len(payload) != 20+size+key_size:
        raise ValueError('Nieprawidłowe rozmiary zawartości')
    with tempfile.TemporaryDirectory(prefix='.wp-restore-', dir=destination.parent) as folder:
        database = Path(folder)/'database.sqlite3'
        ring = Path(folder)/'database.sqlite3.checkout-key'
        _write_private(database, memoryview(payload)[20:20+size])
        _write_private(ring, memoryview(payload)[20+size:])
        result = snapshot(database, ring, destination, restore=True)
    return {**result, 'encrypted_backup': True}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='operation', required=True)
    key = commands.add_parser('init-key')
    key.add_argument('--backup-key', required=True, type=Path)
    backup = commands.add_parser('backup')
    backup.add_argument('--source', required=True, type=Path)
    backup.add_argument('--checkout-key', required=True, type=Path)
    backup.add_argument('--backup-key', required=True, type=Path)
    backup.add_argument('--destination', required=True, type=Path)
    restore = commands.add_parser('restore')
    restore.add_argument('--archive', required=True, type=Path)
    restore.add_argument('--backup-key', required=True, type=Path)
    restore.add_argument('--destination', required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        if args.operation == 'init-key':
            result = make_backup_key(args.backup_key)
        elif args.operation == 'backup':
            result = encrypted_backup(args.source, args.checkout_key, args.backup_key, args.destination)
        else:
            result = encrypted_restore(args.archive, args.backup_key, args.destination)
    except (OSError, ValueError, sqlite3.Error, TimeoutError):
        print('Operacja nieudana. Sprawdź klucz, integralność kopii, limit rozmiaru i nowy cel.', file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

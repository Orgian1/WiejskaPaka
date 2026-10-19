"""Offline test-environment snapshots; never overwrite a database or start traffic."""
import argparse
from contextlib import closing
import json
import math
import os
from pathlib import Path
import shutil
import sqlite3
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _validate(con, key_file):
    from backend.checkout_vault import Vault, read_ring
    from backend.payment_integrity import audit_payment_integrity
    if con.execute('PRAGMA integrity_check').fetchall() != [('ok',)]:
        raise ValueError('Nieprawidłowa integralność bazy')
    if con.execute('PRAGMA foreign_key_check').fetchone() is not None:
        raise ValueError('Nieprawidłowe klucze obce')
    con.row_factory = sqlite3.Row
    active, keys = read_ring(key_file)
    vault = Vault(active, keys)
    for row in con.execute('SELECT buyer_id,request_key,payload_hash,response_json FROM checkout_idempotency'):
        vault.open(row['response_json'], row['buyer_id'], row['request_key'],
                   row['payload_hash'], expose_pin=False)
    audit = audit_payment_integrity(con)
    if not audit['ok']:
        raise ValueError('Niespójne symulacje płatności')
    return {'orders': con.execute('SELECT COUNT(*) FROM orders').fetchone()[0],
            'payments_checked': audit['checked_payments']}


def snapshot(source, key_file, destination, *, restore=False, timeout=30):
    """Create an exclusive private directory, check snapshot, revoke restored sessions.

    Caller must stop key rotation. Destination must be outside the source folder
    used for serving files. Copies contain personal data and are NOT encrypted.
    """
    from backend.checkout_vault import b64, canonical, read_ring, sync_directory
    source, key_file, destination = map(Path, (source, key_file, destination))
    if not math.isfinite(timeout) or timeout <= 0:
        raise ValueError('Limit czasu musi być dodatni')
    if source.is_symlink() or not source.is_file():
        raise ValueError('Wymagany zwykły istniejący plik SQLite')
    # Read key securely before creating anything; never generate replacement keys.
    active, keys = read_ring(key_file)
    key_bytes = canonical({"active": active, "keys": {kid: b64(key) for kid, key in keys.items()}})
    destination.mkdir(mode=0o700, parents=False, exist_ok=False)
    try:
        database = destination / 'database.sqlite3'
        copied_key = destination / 'database.sqlite3.checkout-key'
        for path, content in ((database, b''), (copied_key, key_bytes)):
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, 'wb') as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
        started = time.monotonic()
        def progress(status, remaining, total):
            if time.monotonic() - started > timeout:
                raise TimeoutError('Przekroczono limit kopiowania SQLite')
        with closing(sqlite3.connect(source.resolve().as_uri() + '?mode=ro', uri=True)) as src:
            with closing(sqlite3.connect(database)) as dst:
                src.backup(dst, pages=256, progress=progress, sleep=0.05)
                counts = _validate(dst, copied_key)
                if restore:
                    with dst:
                        revoked = dst.execute('DELETE FROM sessions').rowcount
                        if dst.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='password_reset_tokens'").fetchone():
                            dst.execute('DELETE FROM password_reset_tokens')
                        if dst.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='reset_mail_queue'").fetchone():
                            from backend.reset_mail_queue import quarantine_restored
                            quarantine_restored(dst)
                            if dst.execute("SELECT COUNT(*) FROM reset_mail_queue WHERE state IN ('queued','leased') OR payload IS NOT NULL").fetchone()[0]:
                                raise ValueError('Nie udało się zablokować historycznej kolejki')
                    if dst.execute('SELECT COUNT(*) FROM sessions').fetchone()[0]:
                        raise ValueError('Nie udało się unieważnić sesji')
                else:
                    revoked = 0
        # Detect a changed ring; rotation must remain stopped for the operation.
        if read_ring(key_file) != (active, keys):
            raise ValueError('Klucz zmienił się podczas kopiowania')
        # Windows FlushFileBuffers requires a handle opened for writing.
        with database.open('r+b') as stream:
            os.fsync(stream.fileno())
        sync_directory(destination)
        sync_directory(destination.parent)
        return {**counts, 'restored': restore, 'revoked_sessions': revoked,
                'encrypted_backup': False}
    except BaseException:
        shutil.rmtree(destination)
        raise


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=('backup', 'restore'))
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--key-file', required=True, type=Path)
    parser.add_argument('--destination', required=True, type=Path)
    parser.add_argument('--timeout', type=float, default=30)
    args = parser.parse_args(argv)
    try:
        result = snapshot(args.source, args.key_file, args.destination,
                          restore=args.operation == 'restore', timeout=args.timeout)
    except (OSError, ValueError, sqlite3.Error, TimeoutError):
        print('Operacja nieudana. Źródło nie zostało zmienione; sprawdź pliki, klucz i integralność.', file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

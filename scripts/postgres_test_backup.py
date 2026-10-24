"""Encrypted local PostgreSQL 16/17 test backup and isolated restore rehearsal.

Never restores over an existing database. The rehearsal database is always
randomly created and removed; this is not a production recovery command.
"""
import argparse
import json
import os
from pathlib import Path
import re
import secrets
import selectors
import struct
import subprocess
import sys
import tempfile
import time
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from backend.checkout_vault import Vault, read_ring
from backend.postgres_test_guard import require_disposable_postgres
from backend.test_server_preflight import check_test_server
from backend.test_server_launcher import verify_test_database_connection
from scripts.encrypted_sqlite_snapshot import (
    _publish, _read_regular, _separate_key, _write_private, make_backup_key,
)

MAGIC = b'WPPGBK1\0'
INNER = b'WPPGD01\0'
HEADER_SIZE = 44
MAX_DUMP = 64 * 1024 * 1024
MAX_RING = 16384
MAX_ARCHIVE = HEADER_SIZE + 16 + 20 + MAX_DUMP + MAX_RING


def require_supported_server(version_number):
    if type(version_number) is not int or version_number // 10000 not in (16, 17):
        raise ValueError('PostgreSQL server 16 or 17 required')


def local_parameters(dsn):
    """Reject remote connections and all routing overrides, including PG env."""
    require_disposable_postgres(dsn, environ={})
    check_test_server({'WP_ENV': 'test', 'WP_TEST_DATABASE_URL': dsn})
    from psycopg.conninfo import conninfo_to_dict
    parameters = conninfo_to_dict(dsn)
    # Pin the network endpoint even if the parent has PGHOSTADDR/PGSERVICE.
    parameters.update(hostaddr='127.0.0.1' if parameters['host'] == 'localhost' else parameters['host'],
                      port=parameters.get('port', '5432'),
                      sslmode=parameters.get('sslmode', 'prefer'),
                      passfile=os.devnull,
                      options='-c statement_timeout=120000 -c lock_timeout=5000')
    return parameters


def client_environment(parameters, *, readonly=False):
    # Do not inherit PGSERVICE, PGOPTIONS, PGPASSFILE or other libpq controls.
    env = {key: os.environ[key] for key in ('PATH', 'SystemRoot', 'TEMP', 'TMP') if key in os.environ}
    for source, target in (('host', 'PGHOST'), ('port', 'PGPORT'),
                           ('dbname', 'PGDATABASE'), ('user', 'PGUSER'), ('password', 'PGPASSWORD')):
        if source in parameters:
            env[target] = parameters[source]
    env.update(PGCONNECT_TIMEOUT='5', PGSSLMODE=parameters.get('sslmode', 'prefer'),
               PGAPPNAME='wp_backup_rehearsal', LC_ALL='C',
               PGOPTIONS='-c statement_timeout=120000 -c lock_timeout=5000' +
               (' -c default_transaction_read_only=on' if readonly else ''))
    return env


def require_supported_client(program):
    result = subprocess.run([program, '--version'], stdout=subprocess.PIPE,
                            stderr=subprocess.DEVNULL, timeout=5, check=True)
    if not re.fullmatch(rb'pg_(?:dump|restore) \(PostgreSQL\) (?:16|17)\.[^\r\n]+\r?\n?', result.stdout):
        raise ValueError('PostgreSQL client 16 or 17 required')


def bounded_dump(parameters, *, timeout=120, maximum=MAX_DUMP):
    """Bound memory/time; no plaintext dump file and no printed driver errors."""
    if os.name != 'posix':
        raise ValueError('Native backup requires POSIX')
    require_supported_client('pg_dump')
    process = subprocess.Popen(['pg_dump', '--format=custom', '--no-owner', '--no-acl', '--no-password'],
                               env=client_environment(parameters, readonly=True),
                               stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    data = bytearray()
    deadline = time.monotonic() + timeout
    try:
        with selectors.DefaultSelector() as selector:
            selector.register(process.stdout, selectors.EVENT_READ)
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError('Dump timed out')
                if not selector.select(min(remaining, 1)):
                    continue
                chunk = os.read(process.stdout.fileno(), min(65536, maximum + 1 - len(data)))
                if not chunk:
                    break
                data.extend(chunk)
                if len(data) > maximum:
                    raise ValueError('Dump exceeds limit')
        if process.wait(timeout=max(.01, deadline - time.monotonic())) != 0:
            raise ValueError('Dump failed')
        if not data.startswith(b'PGDMP'):
            raise ValueError('Expected custom dump')
        return bytes(data)
    finally:
        if process.poll() is None:
            process.kill()
        process.wait(timeout=5)
        process.stdout.close()


def backup(dsn, checkout_key, backup_key, destination):
    destination = Path(destination)
    if destination.exists() or destination.is_symlink():
        raise FileExistsError('Archive exists')
    parameters = local_parameters(dsn)
    # Force the Python-side identity/schema probe read-only too.
    import psycopg
    def connect(url, **kwargs):
        connection = psycopg.connect(**{**parameters, **kwargs, 'options':
            '-c default_transaction_read_only=on -c statement_timeout=5000 -c lock_timeout=1000'})
        try:
            require_supported_server(connection.info.server_version)
        except ValueError:
            connection.close()
            raise
        return connection
    verify_test_database_connection(dsn, parameters['dbname'], connect=connect, require_schema=True)
    active, keys = _separate_key(destination, backup_key)
    live_ring = read_ring(checkout_key)
    if set(keys.values()) & set(live_ring[1].values()):
        raise ValueError('Independent backup key required')
    ring = _read_regular(checkout_key, MAX_RING)
    # Confirm that bundled bytes are exactly the validated private ring.
    with tempfile.TemporaryDirectory(prefix='wp-key-check-') as folder:
        key = Path(folder) / 'key'
        _write_private(key, ring)
        if read_ring(key) != live_ring:
            raise ValueError('Checkout key changed')
    dump = bounded_dump(parameters)
    payload = INNER + struct.pack('>QI', len(dump), len(ring)) + dump + ring
    nonce = secrets.token_bytes(12)
    header = MAGIC + active.encode('ascii') + nonce
    archive = header + AESGCM(keys[active]).encrypt(nonce, payload, header)
    if read_ring(checkout_key) != live_ring or read_ring(backup_key) != (active, keys):
        raise ValueError('Key changed during backup')
    _publish(destination, archive)
    return {'success': True, 'encrypted_backup': True, 'restore_verified': False}


def authenticated_contents(archive, backup_key):
    _, keys = _separate_key(archive, backup_key)
    data = _read_regular(archive, MAX_ARCHIVE)
    if len(data) < HEADER_SIZE + 36 or data[:8] != MAGIC:
        raise ValueError('Invalid archive')
    header = data[:HEADER_SIZE]
    try:
        key = keys[header[8:32].decode('ascii')]
        payload = AESGCM(key).decrypt(header[32:44], data[HEADER_SIZE:], header)
    except (InvalidTag, KeyError, UnicodeError):
        raise ValueError('Archive authentication failed') from None
    if len(payload) < 20 or payload[:8] != INNER:
        raise ValueError('Invalid contents')
    size, ring_size = struct.unpack('>QI', payload[8:20])
    if not 5 <= size <= MAX_DUMP or not 0 < ring_size <= MAX_RING or len(payload) != 20 + size + ring_size:
        raise ValueError('Invalid content sizes')
    dump, ring = payload[20:20+size], payload[20+size:]
    if not dump.startswith(b'PGDMP'):
        raise ValueError('Invalid dump')
    with tempfile.TemporaryDirectory(prefix='wp-restore-key-') as folder:
        path = Path(folder) / 'checkout-key'
        _write_private(path, ring)
        keyring = read_ring(path)
    return dump, keyring


def restore_dump(dump, parameters):
    require_supported_client('pg_restore')
    result = subprocess.run(['pg_restore', '--exit-on-error', '--single-transaction',
                             '--no-owner', '--no-acl', '--no-password', '--dbname', parameters['dbname']],
                            input=dump, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                            env=client_environment(parameters), timeout=120)
    if result.returncode:
        raise ValueError('Restore failed')


def validate_restored(connection, keyring):
    from backend.pg_adapter import PgConnection
    from backend.payment_integrity import audit_payment_integrity
    con = PgConnection(connection)
    vault = Vault(*keyring)
    count = 0
    for row in con.execute('SELECT buyer_id,request_key,payload_hash,response_json FROM checkout_idempotency'):
        vault.open(row['response_json'], row['buyer_id'], row['request_key'], row['payload_hash'], expose_pin=False)
        count += 1
    if not audit_payment_integrity(con)['ok']:
        raise ValueError('Restored payment integrity failed')
    orders = con.execute('SELECT count(*) AS n FROM orders').fetchone()['n']
    revoked = con.execute('DELETE FROM sessions').rowcount
    con.execute('DELETE FROM password_reset_tokens')
    if con.execute("SELECT to_regclass('public.reset_mail_queue') AS queue_table").fetchone()['queue_table'] is not None:
        from backend.reset_mail_queue import quarantine_restored
        quarantine_restored(con)
        if con.execute("SELECT count(*) AS n FROM reset_mail_queue WHERE state IN ('queued','leased') OR payload IS NOT NULL").fetchone()['n']:
            raise ValueError('Restored mail queue remains active')
    if con.execute("SELECT to_regclass('public.order_mail_outbox') AS outbox_table").fetchone()['outbox_table'] is not None:
        from backend.order_mail_outbox import quarantine_restored as quarantine_orders
        quarantine_orders(con)
        if con.execute("SELECT count(*) AS n FROM order_mail_outbox WHERE state IN ('queued','started')").fetchone()['n']:
            raise ValueError('Restored purchase mail remains active')
    if (con.execute('SELECT count(*) AS n FROM sessions').fetchone()['n']
            or con.execute('SELECT count(*) AS n FROM password_reset_tokens').fetchone()['n']):
        raise ValueError('Restored sessions remain')
    return {'orders_checked': orders, 'checkout_replies_checked': count, 'sessions_revoked': revoked}


def rehearse(archive, backup_key, admin_dsn):
    # Authentication and key validation precede even the administrative connection.
    dump, keyring = authenticated_contents(archive, backup_key)
    parameters = local_parameters(admin_dsn)
    import psycopg
    from psycopg import sql
    from psycopg.rows import dict_row
    target = 'wp_test_restore_' + uuid4().hex
    created = False
    with psycopg.connect(**parameters, autocommit=True, connect_timeout=5) as admin:
        try:
            require_supported_server(int(admin.execute('SHOW server_version_num').fetchone()[0]))
            admin.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(target)))
            created = True
            restored = {**parameters, 'dbname': target}
            restore_dump(dump, restored)
            with psycopg.connect(**restored, row_factory=dict_row, connect_timeout=5) as connection:
                result = validate_restored(connection, keyring)
        finally:
            if created:
                admin.execute(sql.SQL('DROP DATABASE {} WITH (FORCE)').format(sql.Identifier(target)))
    return {**result, 'success': True, 'restore_verified': True,
            'rehearsal_database_removed': True, 'application_started': False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='operation', required=True)
    for name in ('init-key', 'backup', 'rehearse'):
        child = commands.add_parser(name)
        child.add_argument('--backup-key', type=Path, required=True)
        if name == 'backup':
            child.add_argument('--checkout-key', type=Path, required=True)
            child.add_argument('--destination', type=Path, required=True)
        elif name == 'rehearse':
            child.add_argument('--archive', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.operation == 'init-key':
            result = make_backup_key(args.backup_key)
        elif args.operation == 'backup':
            result = backup(os.environ.get('WP_TEST_DATABASE_URL', ''), args.checkout_key,
                            args.backup_key, args.destination)
        else:
            result = rehearse(args.archive, args.backup_key, os.environ.get('WP_TEST_POSTGRES_DSN', ''))
    except Exception:
        # Driver/subprocess exceptions may embed passwords and connection details.
        print(json.dumps({'success': False, 'error': 'BACKUP_OR_REHEARSAL_FAILED'}))
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

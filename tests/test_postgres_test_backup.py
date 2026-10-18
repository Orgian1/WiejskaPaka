"""Safety properties of encrypted test backups; native recovery has its own gate."""
import json
import os
from pathlib import Path
import secrets
import struct
import subprocess
import sys

import pytest
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from backend.checkout_vault import canonical, create_ring, b64, read_ring
from scripts import postgres_test_backup as pg


@pytest.fixture
def archive(tmp_path):
    keys = tmp_path/'keys';keys.mkdir()
    copies = tmp_path/'copies';copies.mkdir()
    backup_key = keys/'key';pg.make_backup_key(backup_key)
    checkout = keys/'checkout';create_ring(checkout)
    active, keys = read_ring(backup_key)
    nonce = secrets.token_bytes(12)
    header = pg.MAGIC + active.encode() + nonce
    ring = checkout.read_bytes()
    dump = b'PGDMPtest-only'
    payload = pg.INNER + struct.pack('>QI', len(dump), len(ring)) + dump + ring
    path = copies/'copy.wpbackup'
    path.write_bytes(header + AESGCM(keys[active]).encrypt(nonce, payload, header))
    return path, backup_key, checkout


def test_authenticated_archive_contains_matching_checkout_key(archive):
    path, key, checkout = archive
    dump, ring = pg.authenticated_contents(path, key)
    assert dump == b'PGDMPtest-only' and ring == read_ring(checkout)


@pytest.mark.parametrize('kind', ['ciphertext', 'header', 'truncated', 'wrong-key', 'wrong-format'])
def test_reject_bad_archive_before_database_connection(archive, monkeypatch, kind):
    path, key, _ = archive
    data = bytearray(path.read_bytes())
    if kind == 'ciphertext':data[-1] ^= 1
    elif kind == 'header':data[32] ^= 1
    elif kind == 'truncated':data = data[:50]
    elif kind == 'wrong-format':data[:8] = b'WPSNAP1\0'
    else:
        other = key.parent/'other';pg.make_backup_key(other);key = other
    path.write_bytes(data)
    monkeypatch.setattr(pg, 'local_parameters', lambda *_: pytest.fail('No DB work before authentication'))
    with pytest.raises(ValueError):pg.rehearse(path, key, 'private-dsn')


@pytest.mark.parametrize('dsn', [
    'postgresql://a:b@example.invalid/wp_test_x',
    'postgresql://a:b@127.0.0.1/production',
    'postgresql://a:b@127.0.0.1/wp_test_x?host=remote',
    'postgresql://a:b@127.0.0.1/wp_test_x?sslmode=prefer&sslmode=disable',
    'postgresql://a:b@127.0.0.1/wp_test_x?application_name=x&application_name=y',
])
def test_refuse_ambiguous_or_remote_targets(dsn):
    with pytest.raises(ValueError):pg.local_parameters(dsn)


def test_subprocess_credentials_are_not_argv_or_inherited_pg_settings(monkeypatch):
    for name in ('PGSERVICE', 'PGPASSFILE', 'PGHOSTADDR', 'PGOPTIONS'):
        monkeypatch.setenv(name, 'DO-NOT-INHERIT')
    env = pg.client_environment({'host':'127.0.0.1', 'dbname':'wp_test_x',
        'password':'private-password', 'user':'restricted'}, readonly=True)
    assert not {'PGSERVICE','PGPASSFILE','PGHOSTADDR'} & env.keys()
    assert 'DO-NOT-INHERIT' not in json.dumps(env)
    assert 'default_transaction_read_only=on' in env['PGOPTIONS']
    assert env['PGPASSWORD'] == 'private-password'


def test_backup_never_overwrites_destination(archive):
    path, key, checkout = archive
    before = path.read_bytes()
    with pytest.raises(FileExistsError):pg.backup('invalid', checkout, key, path)
    assert path.read_bytes() == before


def test_key_cannot_be_kept_beside_archive(archive):
    path, key, _ = archive
    same = path.parent/'key';same.write_bytes(key.read_bytes());same.chmod(0o600)
    with pytest.raises(ValueError):pg.authenticated_contents(path, same)


def test_cli_sanitizes_all_driver_errors(monkeypatch, capsys):
    def fail(*_):raise RuntimeError('postgresql://secret:password@private/db')
    monkeypatch.setattr(pg, 'rehearse', fail)
    assert pg.main(['rehearse', '--archive','file','--backup-key','key']) == 1
    out = capsys.readouterr()
    assert json.loads(out.out) == {'success':False,'error':'BACKUP_OR_REHEARSAL_FAILED'}
    assert not out.err and 'password' not in out.out


@pytest.mark.skipif(os.name != 'posix', reason='POSIX bounded pipe runner')
@pytest.mark.parametrize('kind', ['valid', 'oversized', 'timeout', 'exit-error', 'wrong-format'])
def test_dump_process_is_bounded_and_reaped(monkeypatch, kind):
    real_popen = subprocess.Popen
    children = []
    code = {'valid':"import os;os.write(1,b'PGDMPtest')",
            'oversized':"import os;os.write(1,b'PGDMP'+b'x'*10000)",
            'timeout':"import time;time.sleep(30)",
            'exit-error':"raise SystemExit(3)",
            'wrong-format':"print('not a dump')"}[kind]
    def launch(command, **kwargs):
        assert 'private-password' not in repr(command)
        process = real_popen([sys.executable, '-c', code], **kwargs)
        children.append(process)
        return process
    monkeypatch.setattr(pg, 'require_client16', lambda _: None)
    monkeypatch.setattr(pg.subprocess, 'Popen', launch)
    if kind == 'valid':
        assert pg.bounded_dump({'password':'private-password'}, timeout=2, maximum=32) == b'PGDMPtest'
    else:
        with pytest.raises((ValueError, TimeoutError)):
            pg.bounded_dump({'password':'private-password'}, timeout=.2, maximum=32)
    assert children[0].poll() is not None and children[0].stdout.closed


def test_python_database_endpoint_is_pinned_against_inherited_hostaddr(monkeypatch):
    monkeypatch.setenv('PGHOSTADDR', '198.51.100.1')
    parameters = pg.local_parameters('postgresql://a:b@localhost/wp_test_x')
    assert parameters['hostaddr'] == '127.0.0.1'
    assert parameters['port'] == '5432' and parameters['passfile'] == os.devnull
    assert parameters['options'].startswith('-c statement_timeout=')


@pytest.mark.parametrize('variant', ['shared-key', 'key-changed', 'success'])
def test_backup_key_separation_rotation_and_private_publication(archive, monkeypatch, variant):
    path, key, checkout = archive
    path.unlink()
    monkeypatch.setattr(pg, 'local_parameters', lambda _: {'dbname':'wp_test_x'})
    monkeypatch.setattr(pg, 'verify_test_database_connection', lambda *a, **kw: None)
    if variant == 'shared-key':
        key.write_bytes(checkout.read_bytes())
    def dump(_):
        if variant == 'key-changed':
            checkout.unlink();create_ring(checkout)
        return b'PGDMPdump'
    monkeypatch.setattr(pg, 'bounded_dump', dump)
    if variant == 'success':
        assert pg.backup('private', checkout, key, path)['success']
        assert pg.authenticated_contents(path, key)[0] == b'PGDMPdump'
        if os.name == 'posix':assert path.stat().st_mode & 0o077 == 0
    else:
        with pytest.raises(ValueError):pg.backup('private', checkout, key, path)
        assert not path.exists()


@pytest.mark.parametrize('failure', ['restore', 'validation', 'none'])
def test_rehearsal_drops_only_its_created_database_even_after_failure(archive, monkeypatch, failure):
    path, key, _ = archive
    import psycopg
    from psycopg import sql
    commands = []
    class Connection:
        def __enter__(self):return self
        def __exit__(self, *_):pass
        def execute(self, command):
            text = command.as_string() if isinstance(command, sql.Composable) else command
            commands.append(text)
            return self
        def fetchone(self):return ('160010',)
    monkeypatch.setattr(psycopg, 'connect', lambda **_: Connection())
    monkeypatch.setattr(pg, 'local_parameters', lambda _: {'dbname':'wp_test_seed'})
    def restore(_, parameters):
        assert parameters['dbname'].startswith('wp_test_restore_')
        if failure == 'restore':raise ValueError('private')
    def validate(*_):
        if failure == 'validation':raise ValueError('private')
        return {'orders_checked':1}
    monkeypatch.setattr(pg, 'restore_dump', restore)
    monkeypatch.setattr(pg, 'validate_restored', validate)
    if failure == 'none':
        assert pg.rehearse(path, key, 'private')['rehearsal_database_removed']
    else:
        with pytest.raises(ValueError):pg.rehearse(path, key, 'private')
    assert len(commands) == 3
    created = commands[1].split('"')[1]
    dropped = commands[2].split('"')[1]
    assert created == dropped and created.startswith('wp_test_restore_')
    assert 'wp_test_seed' not in ''.join(commands)

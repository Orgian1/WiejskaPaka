"""Real loopback HTTP with disposable DB and synthetic keys; no SMTP."""
import base64
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
import json
import os
import sqlite3
import time

import pytest

from backend import reset_http_config, reset_mail_keys, reset_mail_queue as queue
from scripts.run_phone_demo import demo_environment
from scripts.run_tests_isolated import test_environment as isolated_environment
from tests.test_purchase_record_http_restart import server
from tests.test_password_reset_http import register, EMAIL, OLD, NEW


@pytest.fixture
def keys_file(tmp_path):
    if os.name != 'posix':
        pytest.skip('private key loader requires POSIX')
    path = tmp_path/'synthetic-keys.json'
    path.write_text(json.dumps({'format': 1, 'active': 'v1',
        'keys': {'v1': base64.b64encode(b'q'*32).decode()}}))
    path.chmod(0o600)
    return path


def connect(path):
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    return con


def request(client, email=EMAIL):
    response = client.post('/auth/password-reset/request', json={'email': email})
    assert response.status_code == 202
    assert response.headers['cache-control'] == 'no-store'
    assert email not in response.text
    return response.json()


def confirm(client, token):
    return client.post('/auth/password-reset/confirm', json={'token': token, 'new_password': NEW})


def test_http_queue_restart_confirm_and_no_delivery(tmp_path, keys_file):
    database = tmp_path/'reset.sqlite3'
    with server(database, queued_keys=keys_file) as client:
        session = register(client)
        assert request(client) == request(client, 'unknown@example.invalid')
        assert client.get('/auth/password-reset-test/options').json()['enabled'] is False
        with closing(connect(database)) as con:
            rows = con.execute('SELECT * FROM reset_mail_queue').fetchall()
            assert len(rows) == 1 and rows[0]['state'] == 'queued' and rows[0]['attempts'] == 0
            delivery = reset_mail_keys.load_keys(keys_file).decrypt(rows[0])
            token = delivery.token
            assert EMAIL.encode() not in bytes(rows[0]['payload'])
            assert token.encode() not in bytes(rows[0]['payload'])
            assert con.execute('SELECT COUNT(*) FROM password_reset_tokens').fetchone()[0] == 1
    with server(database, queued_keys=keys_file) as client:
        assert confirm(client, token).status_code == 200
        assert confirm(client, token).status_code == 400
        assert client.get('/auth/me', headers=session).status_code == 401
        assert client.post('/auth/login', json={'email': EMAIL, 'password': OLD}).status_code == 401
        assert client.post('/auth/login', json={'email': EMAIL, 'password': NEW}).status_code == 200
    # Consumed links cannot be delivered even if a future worker claims the job.
    con = connect(database)
    with queue.transaction(con):
        lease = queue.claim(con, now=int(time.time()))
    with queue.transaction(con):
        assert queue.start(con, reset_mail_keys.load_keys(keys_file), lease, now=int(time.time())) is None
    con.close()


def test_http_budget_survives_restart_and_parallel_requests(tmp_path, keys_file):
    database = tmp_path/'limit.sqlite3'
    with server(database, queued_keys=keys_file) as client:
        register(client)
        with ThreadPoolExecutor(max_workers=6) as pool:
            results = list(pool.map(lambda _: request(client, EMAIL.upper()), range(8)))
        assert all(body == results[0] for body in results)
    with server(database, queued_keys=keys_file) as client:
        assert request(client) == results[0]
        with closing(connect(database)) as con:
            assert con.execute('SELECT COUNT(*) FROM reset_mail_queue').fetchone()[0] == 3
            assert con.execute('SELECT COUNT(*) FROM password_reset_tokens').fetchone()[0] == 3


def test_queue_insert_failure_rolls_back_token_and_budget(tmp_path, keys_file):
    database = tmp_path/'rollback.sqlite3'
    with server(database, queued_keys=keys_file) as client:
        register(client)
        with closing(connect(database)) as con, con:
            con.execute("CREATE TRIGGER reject_job BEFORE INSERT ON reset_mail_queue BEGIN SELECT RAISE(ABORT,'synthetic-private-error'); END")
        # An unhandled ASGI failure closes this connection after the safe 500.
        response = client.post('/auth/password-reset/request', json={'email': EMAIL},
                               headers={'Connection': 'close'})
        assert response.status_code == 500
        assert 'synthetic-private-error' not in response.text and EMAIL not in response.text
        with closing(connect(database)) as con, con:
            for table in ('reset_mail_queue', 'password_reset_tokens', 'password_reset_limits'):
                assert con.execute('SELECT COUNT(*) FROM '+table).fetchone()[0] == 0
            con.execute('DROP TRIGGER reject_job')
        request(client)


def test_disabled_and_invalid_requests(tmp_path, keys_file):
    with server(tmp_path/'disabled.sqlite3') as client:
        assert client.post('/auth/password-reset/request', json={'email': EMAIL}).status_code == 404
        assert confirm(client, 'x'*43).status_code == 404
    with server(tmp_path/'validation.sqlite3', queued_keys=keys_file) as client:
        for body in ({'email': 'bad@@example.invalid'}, {'email': EMAIL, 'user_id': 1}):
            response = client.post('/auth/password-reset/request', json=body)
            assert response.status_code == 422 and EMAIL not in response.text


def test_config_disabled_never_reads_keys(monkeypatch):
    monkeypatch.setattr(reset_mail_keys, 'load_config', lambda *a, **kw: pytest.fail('unexpected read'))
    assert reset_http_config.load_config({'WP_ENABLE_MAIL_QUEUE': '1'}, '') is None


@pytest.mark.parametrize('extra,dsn', [
    ({'WP_ENV': 'development'}, ''),
    ({}, ''),
    ({'WP_ENABLE_TEST_PASSWORD_RESET': '1'}, ''),
    ({'WP_ENABLE_MAIL_QUEUE': '1', 'WP_MAIL_QUEUE_KEYS_FILE': 'private-secret'}, ''),
    ({}, 'postgresql://remote.example/production'),
])
def test_config_rejects_unsafe_modes_without_secrets(extra, dsn):
    env = {'WP_ENABLE_QUEUED_PASSWORD_RESET': '1', 'WP_ENV': 'test', **extra}
    with pytest.raises(ValueError, match='^RESET_HTTP_CONFIGURATION_REJECTED$') as error:
        reset_http_config.load_config(env, dsn)
    assert error.value.__cause__ is None


def test_demo_and_runner_strip_queue_opt_ins(tmp_path):
    env = {'WP_ENABLE_QUEUED_PASSWORD_RESET': '1', 'WP_ENABLE_MAIL_QUEUE': '1',
           'WP_MAIL_QUEUE_KEYS_FILE': '/private/synthetic'}
    for sanitized in (demo_environment(env, tmp_path/'demo.sqlite3'),
                      isolated_environment(env, tmp_path/'test.sqlite3')):
        assert all(key not in sanitized for key in env)

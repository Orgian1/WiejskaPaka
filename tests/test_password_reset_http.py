"""Actual HTTP reset links; no real email, account or external delivery."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
import json
import sqlite3

import httpx
import pytest

from scripts.sqlite_snapshot import snapshot
from tests.test_purchase_record_http_restart import server
from tests.test_sqlite_recovery_rehearsal import purchase, key_path

EMAIL, OLD, NEW = 'reset@example.invalid', 'Old-synthetic-password!', 'New-synthetic-password!'


def enable(monkeypatch, tmp_path):
    box = tmp_path/'mailbox'
    return box


def register(client):
    assert client.post('/auth/register', json={'email': EMAIL,'password': OLD,'role':'klient'}).status_code == 201
    return {'Authorization':'Bearer '+client.post('/auth/login',json={'email':EMAIL,'password':OLD}).json()['access_token']}


def request(client, box, email=EMAIL):
    before = set(box.glob('*.json'))
    response = client.post('/auth/password-reset-test/request', json={'email':email})
    assert response.status_code == 202 and response.headers['cache-control'] == 'no-store'
    files = set(box.glob('*.json'))-before
    message = json.loads(files.pop().read_text())
    token = message['fragment'].split('=',1)[1]
    assert token not in response.text and email not in response.text
    return token, response.json()


def confirm(client, token):
    return client.post('/auth/password-reset-test/confirm',json={'token':token,'new_password':NEW})


def test_http_request_confirm_replay_and_other_sessions(monkeypatch,tmp_path):
    box = enable(monkeypatch,tmp_path)
    with server(tmp_path/'demo.sqlite3',reset_outbox=box) as client:
        headers = register(client)
        extra = client.post('/auth/login',json={'email':EMAIL,'password':OLD}).json()['access_token']
        token, body = request(client,box)
        unknown, other_body = request(client,box,'unknown@example.invalid')
        assert body == other_body
        assert confirm(client,unknown).status_code == 400
        assert client.get('/auth/me',headers=headers).status_code == 200
        assert confirm(client,token).status_code == 200
        assert confirm(client,token).status_code == 400
        for h in (headers,{'Authorization':'Bearer '+extra}):
            assert client.get('/auth/me',headers=h).status_code == 401
        assert client.post('/auth/login',json={'email':EMAIL,'password':OLD}).status_code == 401
        assert client.post('/auth/login',json={'email':EMAIL,'password':NEW}).status_code == 200


def test_two_confirmations_have_only_one_winner(monkeypatch,tmp_path):
    box = enable(monkeypatch,tmp_path)
    with server(tmp_path/'race.sqlite3',reset_outbox=box) as client:
        register(client)
        token,_ = request(client,box)
        def run(_):
            with httpx.Client(base_url=str(client.base_url),trust_env=False,timeout=20) as other:
                return confirm(other,token).status_code
        with ThreadPoolExecutor(max_workers=2) as pool:
            assert sorted(pool.map(run,range(2))) == [200,400]


def test_reset_does_not_mutate_purchases_and_restore_revokes_pending_links(monkeypatch,tmp_path):
    box = enable(monkeypatch,tmp_path)
    database = tmp_path/'purchase.sqlite3'
    with server(database,reset_outbox=box) as client:
        _, buyer, _, _, _, _, url, record = purchase(client)
        register(client)
        token,_ = request(client,box)
        assert confirm(client,token).status_code == 200
        assert client.get(url,headers=buyer).json() == record
        pending,_ = request(client,box)
        snapshot(database,key_path(database),tmp_path/'restored',restore=True)
    with closing(sqlite3.connect(tmp_path/'restored'/'database.sqlite3')) as con:
        assert con.execute('SELECT COUNT(*) FROM password_reset_tokens').fetchone()[0] == 0
        assert con.execute('SELECT COUNT(*) FROM orders').fetchone()[0] == 2
    with server(tmp_path/'restored'/'database.sqlite3',reset_outbox=box) as client:
        assert confirm(client,pending).status_code == 400


def test_disabled_routes_and_validation_do_not_disclose_secret(monkeypatch,tmp_path):
    monkeypatch.delenv('WP_ENABLE_TEST_PASSWORD_RESET',raising=False)
    monkeypatch.delenv('WP_TEST_RESET_OUTBOX',raising=False)
    with server(tmp_path/'disabled.sqlite3') as client:
        assert client.get('/auth/password-reset-test/options').json()['enabled'] is False
        response = confirm(client,'sensitive-synthetic-token')
        assert response.status_code == 404
        assert 'sensitive-synthetic-token' not in response.text
        response = client.post('/auth/password-reset-test/confirm',json={'token':'x','new_password':'shortkey'})
        assert response.status_code == 422 and 'shortkey' not in response.text


def test_request_limit_and_token_survive_process_restart(monkeypatch,tmp_path):
    box = enable(monkeypatch,tmp_path)
    database = tmp_path/'restart.sqlite3'
    with server(database,reset_outbox=box) as client:
        register(client)
        tokens = [request(client,box)[0] for _ in range(3)]
        response = client.post('/auth/password-reset-test/request',json={'email':EMAIL.upper()})
        assert response.status_code == 202 and len(list(box.glob('*.json'))) == 3
    with server(database,reset_outbox=box) as client:
        response = client.post('/auth/password-reset-test/request',json={'email':EMAIL})
        assert response.status_code == 202 and len(list(box.glob('*.json'))) == 3
        assert confirm(client,tokens[0]).status_code == 200
        assert confirm(client,tokens[1]).status_code == 400
        assert confirm(client,tokens[2]).status_code == 400


def test_email_or_account_id_cannot_replace_reset_token(monkeypatch,tmp_path):
    box = enable(monkeypatch,tmp_path)
    with server(tmp_path/'identity.sqlite3',reset_outbox=box) as client:
        headers = register(client)
        for body in ({'email':EMAIL,'new_password':NEW},
                     {'user_id':1,'new_password':NEW},
                     {'token':'x'*43,'user_id':1,'new_password':NEW}):
            response = client.post('/auth/password-reset-test/confirm',json=body)
            assert response.status_code == 422
        assert confirm(client,'x'*43).status_code == 400
        assert client.get('/auth/me',headers=headers).status_code == 200

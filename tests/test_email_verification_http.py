"""Real authenticated HTTP; private queue inspected locally, never live email."""
import base64
from contextlib import closing
import json
import os
import sqlite3
import pytest
from backend.reset_mail_queue import KeyRing
from tests.test_purchase_record_http_restart import server, account


@pytest.fixture
def enabled(tmp_path,monkeypatch):
    if os.name!='posix':pytest.skip('Private external POSIX queue key loader')
    path=tmp_path/'keys.json'
    path.write_text(json.dumps({'format':1,'active':'test','keys':{'test':base64.b64encode(b'v'*32).decode()}}))
    path.chmod(0o600)
    monkeypatch.setenv('WP_ENABLE_EMAIL_VERIFICATION','1')
    monkeypatch.setenv('WP_ENABLE_MAIL_QUEUE','1')
    monkeypatch.setenv('WP_MAIL_QUEUE_KEYS_FILE',str(path))
    return tmp_path/'api.sqlite3',KeyRing({'test':b'v'*32},'test'),path


def queued(database,keys):
    with closing(sqlite3.connect(database)) as con:
        con.row_factory=sqlite3.Row
        return keys.decrypt(con.execute('SELECT * FROM email_verification_queue').fetchone())


def test_authenticated_roundtrip_no_token_in_api_and_survives_restart(enabled):
    database,keys,key_path=enabled
    with server(database,verification_keys=key_path) as client:
        headers=account(client,'klient');other=account(client,'klient')
        assert client.get('/auth/email-verification/options').json()=={'enabled':True}
        assert client.post('/auth/email-verification/request').status_code==401
        assert client.get('/auth/email-verification/status',headers=headers).json()=={'verified':False}
        response=client.post('/auth/email-verification/request',headers=headers)
        assert response.status_code==202
        secret=queued(database,keys).token
        assert secret not in response.text and 'token' not in response.text
        assert client.post('/auth/email-verification/confirm',headers=other,json={'token':secret}).status_code==400
        assert client.post('/auth/email-verification/confirm',headers=headers,json={'token':secret,'user_id':1}).status_code==422
        assert client.post('/auth/email-verification/confirm',headers=headers,json={'token':secret}).json()=={'verified':True}
        assert client.post('/auth/email-verification/confirm',headers=headers,json={'token':secret}).status_code==400
    with server(database,verification_keys=key_path) as client:
        assert client.get('/auth/email-verification/status',headers=headers).json()=={'verified':True}
        with closing(sqlite3.connect(database)) as con:
            state,payload=con.execute('SELECT state,payload FROM email_verification_queue').fetchone()
            assert state=='expired' and payload is None


def test_rate_limit_is_committed_and_persists_after_restart(enabled):
    database,_,key_path=enabled
    with server(database,verification_keys=key_path) as client:
        headers=account(client,'rolnik')
        for _ in range(5):assert client.post('/auth/email-verification/request',headers=headers).status_code==202
        assert client.post('/auth/email-verification/request',headers=headers).status_code==429
    with server(database,verification_keys=key_path) as client:
        assert client.post('/auth/email-verification/request',headers=headers).status_code==429


def test_default_disabled(tmp_path,monkeypatch):
    monkeypatch.delenv('WP_ENABLE_EMAIL_VERIFICATION',raising=False)
    with server(tmp_path/'disabled.sqlite3') as client:
        headers=account(client,'klient')
        assert client.get('/auth/email-verification/options').json()=={'enabled':False}
        assert client.get('/auth/email-verification/status',headers=headers).status_code==404
        assert client.post('/auth/email-verification/request',headers=headers).status_code==404

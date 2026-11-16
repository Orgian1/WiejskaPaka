"""Disposable contact mailbox: real HTTP, replay safety, private admin read."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
import json
import os
from pathlib import Path
import sqlite3
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
import pytest

from backend.contact_demo import ContactMessage, Mailbox, install
from tests.test_purchase_record_http_restart import server
from tests.test_postgres_full_api_optin import register


def message(**changes):
    return {'request_key':str(uuid4()),'topic':'contact','email':'guest@example.invalid',
            'subject':'Pytanie demonstracyjne','message':'Wiadomość testowa bez prawdziwych danych.',**changes}


def admin_account(client, database):
    headers,uid=register(client,'klient')
    with closing(sqlite3.connect(database)) as con:
        con.execute("UPDATE users SET role='admin' WHERE id=?",(uid,));con.commit()
    return headers


def test_http_public_submit_admin_only_read_and_restart(tmp_path):
    database=tmp_path/'contact.sqlite3';outbox=tmp_path/'mailbox';body=message(topic='problem')
    with server(database,contact_outbox=outbox) as client:
        admin=admin_account(client,database);buyer,_=register(client,'klient');seller,_=register(client,'rolnik')
        assert client.get('/test/contact/options').json()=={'enabled':True,'mode':'local_test'}
        created=client.post('/test/contact/messages',json=body)
        assert created.status_code==202,created.text
        assert created.json()=={'id':body['request_key'],'mode':'local_test','stored':True}
        assert created.headers['cache-control']=='no-store'
        assert body['email'] not in created.text and body['message'] not in created.text
        assert client.get('/test/admin/contact/messages').status_code==401
        for actor in [buyer,seller]:assert client.get('/test/admin/contact/messages',headers=actor).status_code==403
        listed=client.get('/test/admin/contact/messages',headers=admin)
        assert listed.status_code==200 and listed.headers['cache-control']=='no-store'
        item=listed.json()['items'][0]
        assert item['message']==body['message'] and item['topic']=='problem' and item['test_only']
        assert 'fingerprint' not in item
        assert client.get('/test/admin/contact/messages?limit=21',headers=admin).status_code==422
    with server(database,contact_outbox=outbox) as client:
        assert client.post('/test/contact/messages',json=body).status_code==202
        assert client.get('/test/admin/contact/messages',headers=admin).json()['total']==1
    files=list(outbox.glob('*.json'));assert len(files)==1
    if os.name=='posix':assert files[0].stat().st_mode&0o077==0


def test_parallel_retry_does_not_duplicate_and_mismatched_retry_is_rejected(tmp_path):
    with server(tmp_path/'retry.sqlite3',contact_outbox=tmp_path/'mail') as client:
        body=message()
        with ThreadPoolExecutor(8) as pool:responses=list(pool.map(lambda _:client.post('/test/contact/messages',json=body),range(12)))
        assert all(r.status_code==202 for r in responses),[r.text for r in responses]
        assert len(list((tmp_path/'mail').glob('*.json')))==1
        assert client.post('/test/contact/messages',json={**body,'message':'Inna wiadomość z tym samym identyfikatorem.'}).status_code==409


def test_rate_limit_does_not_block_replay_or_admin_read(tmp_path):
    with server(tmp_path/'rate.sqlite3',contact_outbox=tmp_path/'mail') as client:
        admin=admin_account(client,tmp_path/'rate.sqlite3');body=message()
        for i in range(5):assert client.post('/test/contact/messages',json=body if i==0 else message()).status_code==202
        limited=client.post('/test/contact/messages',json=message())
        assert limited.status_code==429 and 1<=int(limited.headers['retry-after'])<=3600
        assert client.post('/test/contact/messages',json=body).status_code==202
        assert client.get('/test/admin/contact/messages',headers=admin).json()['total']==5


@pytest.mark.parametrize('changes',[
    {'email':'bad@example.invalid\r\nBcc: victim@example.invalid'},
    {'subject':'Bad\nHeader'}, {'message':'x\x00'*20}, {'message':'short'},
    {'message':'x'*4001}, {'request_key':'../../outside'}, {'topic':'admin'}, {'admin':True},
])
def test_invalid_payload_never_creates_mail(tmp_path,changes):
    with server(tmp_path/'invalid.sqlite3',contact_outbox=tmp_path/'mail') as client:
        assert client.post('/test/contact/messages',json=message(**changes)).status_code==422
    assert not list((tmp_path/'mail').glob('*.json'))


def test_disabled_postgres_and_production_never_create_outbox(tmp_path):
    for extra,dsn in [({},''),({'WP_ENABLE_TEST_CONTACT':'1'},'postgresql://unused.invalid/not-opened'),
                      ({'WP_ENABLE_TEST_CONTACT':'1','WP_ENV':'production'},'')]:
        app=FastAPI();folder=tmp_path/uuid4().hex
        install(app,lambda:{'role':'admin'},{'WP_TEST_CONTACT_OUTBOX':str(folder),**extra},dsn)
        with TestClient(app) as client:
            assert client.get('/test/contact/options').json()=={'enabled':False,'mode':None}
            assert client.post('/test/contact/messages',json=message()).status_code==404
        assert not folder.exists()


def test_storage_error_is_not_reported_as_success_or_leaked(tmp_path,monkeypatch):
    app=FastAPI();install(app,lambda:{'role':'admin'},{'WP_ENABLE_TEST_CONTACT':'1','WP_TEST_CONTACT_OUTBOX':str(tmp_path/'mail')},'')
    def fail(*args):raise OSError('private-server-path-and-secret')
    monkeypatch.setattr(Mailbox,'submit',fail)
    with TestClient(app) as client:
        reply=client.post('/test/contact/messages',json=message())
        assert reply.status_code==503 and 'private-server' not in reply.text


def test_budget_expiry_capacity_and_pagination(tmp_path):
    now=[0.0];box=Mailbox(tmp_path/'mail',clock=lambda:now[0])
    for i in range(5):box.submit(ContactMessage(**message(subject=f'Temat numer {i}')))
    with pytest.raises(HTTPException) as limited:box.submit(ContactMessage(**message()))
    assert limited.value.status_code==429
    now[0]=3600;box.submit(ContactMessage(**message()))
    first=box.listing(0,2);second=box.listing(2,2)
    assert first['total']==6 and first['has_more'] and len(first['items'])==2
    assert not {i['id'] for i in first['items']}&{i['id'] for i in second['items']}
    # Bound storage independently of the per-email budget.
    for _ in range(994):(box.folder/(str(uuid4())+'.json')).touch()
    with pytest.raises(HTTPException) as full:box.submit(ContactMessage(**message(email='other@example.invalid')))
    assert full.value.status_code==503


def test_unsafe_mailbox_paths_fail_closed(tmp_path):
    with pytest.raises(ValueError):Mailbox(Path('relative-contact-folder'))
    with pytest.raises(ValueError):Mailbox(Path(__file__).resolve().parents[1]/'not-created-contact-folder')
    if os.name=='posix':
        folder=tmp_path/'public';folder.mkdir(mode=0o755)
        with pytest.raises(ValueError):Mailbox(folder)
        target=tmp_path/'target';target.mkdir(mode=0o700)
        link=tmp_path/'link';link.symlink_to(target,target_is_directory=True)
        with pytest.raises(ValueError):Mailbox(link)

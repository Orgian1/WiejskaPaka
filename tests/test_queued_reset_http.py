"""Actual HTTP to a synthetic queue, manually drained by an in-memory transport."""
from contextlib import closing
from concurrent.futures import ThreadPoolExecutor
import base64
import json
import os
import sqlite3

import pytest
from backend import reset_mail_queue as queue,reset_mail_keys as keys_loader
from backend.smtp_reset_transport import outcome
from tests.test_password_reset_http import register,confirm,EMAIL,OLD,NEW
from tests.test_purchase_record_http_restart import server

pytestmark=pytest.mark.skipif(os.name!='posix',reason='private queue keys require POSIX')
URL='/auth/password-reset-test/request'


def key_file(tmp_path):
    path=tmp_path/'queue-keys.json'
    path.write_text(json.dumps({'format':1,'active':'v1','keys':{'v1':base64.b64encode(b'a'*32).decode()}}));path.chmod(0o600)
    return path


def connect(database):
    con=sqlite3.connect(database,timeout=15);con.row_factory=sqlite3.Row;return con


def request(client,email=EMAIL):
    response=client.post(URL,json={'email':email})
    assert response.status_code==202 and response.headers['cache-control']=='no-store'
    assert email not in response.text and 'token' not in response.text and 'job' not in response.text
    return response.json()


def test_http_queues_without_filebox_and_manual_transport_completes_reset(tmp_path):
    key=key_file(tmp_path);database=tmp_path/'demo.sqlite3';calls=[]
    with server(database,queued_keys=key) as client:
        auth=register(client)
        before=set(tmp_path.iterdir());known=request(client);unknown=request(client,'unknown@example.invalid')
        assert known==unknown
        with closing(connect(database)) as con:
            rows=con.execute('SELECT * FROM reset_mail_queue').fetchall()
            assert len(rows)==1 and rows[0]['state']=='queued'
            assert EMAIL.encode() not in bytes(rows[0]['payload'])
        assert not [p for p in set(tmp_path.iterdir())-before if p.suffix=='.json']
        keys=keys_loader.load_keys(key)
        def transport(recipient,token):calls.append((recipient,token));return outcome('ACCEPTED',accepted=True)
        import time
        assert queue.dispatch_once(lambda:connect(database),keys,transport,clock=lambda:int(time.time()))=='ACCEPTED'
        assert len(calls)==1 and calls[0][0]==EMAIL
        assert calls[0][1].encode() not in database.read_bytes()
        assert confirm(client,calls[0][1]).status_code==200
        assert confirm(client,calls[0][1]).status_code==400
        assert client.get('/auth/me',headers=auth).status_code==401
        assert client.post('/auth/login',json={'email':EMAIL,'password':OLD}).status_code==401
        assert client.post('/auth/login',json={'email':EMAIL,'password':NEW}).status_code==200


def test_restart_keeps_encrypted_pending_task_and_original_session(tmp_path):
    key=key_file(tmp_path);database=tmp_path/'restart.sqlite3'
    with server(database,queued_keys=key) as client:
        auth=register(client);request(client)
    calls=[]
    with server(database,queued_keys=key) as client:
        assert client.get('/auth/me',headers=auth).status_code==200
        import time
        result=queue.dispatch_once(lambda:connect(database),keys_loader.load_keys(key),
            lambda recipient,token:(calls.append((recipient,token)) or outcome('ACCEPTED',accepted=True)),clock=lambda:int(time.time()))
        assert result=='ACCEPTED' and len(calls)==1 and confirm(client,calls[0][1]).status_code==200


def test_parallel_requests_persist_at_most_three_jobs_and_share_generic_response(tmp_path):
    key=key_file(tmp_path);database=tmp_path/'race.sqlite3'
    with server(database,queued_keys=key) as client:
        register(client)
        with ThreadPoolExecutor(max_workers=8) as pool:bodies=list(pool.map(lambda _:request(client),range(8)))
        assert all(body==bodies[0] for body in bodies)
        with closing(connect(database)) as con:
            assert con.execute('SELECT COUNT(*) FROM reset_mail_queue').fetchone()[0]==3
            assert con.execute('SELECT COUNT(*) FROM password_reset_tokens').fetchone()[0]==3


def test_queue_write_fault_returns_same_public_response_and_rolls_back_everything(tmp_path):
    key=key_file(tmp_path);database=tmp_path/'fault.sqlite3'
    with server(database,queued_keys=key) as client:
        register(client)
        with closing(connect(database)) as con,con:
            con.execute("CREATE TRIGGER queue_fault BEFORE INSERT ON reset_mail_queue BEGIN SELECT RAISE(ABORT,'synthetic-private-fault'); END")
        body=request(client)
        with closing(connect(database)) as con:
            for table in ('reset_mail_queue','password_reset_tokens','password_reset_limits'):
                assert con.execute('SELECT COUNT(*) FROM '+table).fetchone()[0]==0
        assert body==request(client,'unknown@example.invalid')
        with closing(connect(database)) as con,con:con.execute('DROP TRIGGER queue_fault')
        assert request(client)==body
        with closing(connect(database)) as con:assert con.execute('SELECT COUNT(*) FROM reset_mail_queue').fetchone()[0]==1


def test_normal_demo_defaults_off_and_does_not_create_queue(tmp_path):
    database=tmp_path/'disabled.sqlite3'
    with server(database) as client:
        assert client.get('/auth/password-reset-test/options').json()['enabled'] is False
        assert client.post(URL,json={'email':EMAIL}).status_code==404
    with closing(connect(database)) as con:
        assert con.execute("SELECT COUNT(*) FROM sqlite_master WHERE name='reset_mail_queue'").fetchone()[0]==0


@pytest.mark.parametrize('patch',[
 {'WP_ENABLE_TEST_PASSWORD_RESET':'0'}, {'WP_ENV':'development'},
 {'WP_TEST_RESET_OUTBOX':'private-secret-filebox'}, {'WP_ENABLE_MAIL_QUEUE':'0'},
 {'WP_MAIL_QUEUE_KEYS_FILE':'private-secret-relative-path'}])
def test_bad_queue_configuration_blocks_start_with_a_redacted_error(tmp_path,patch):
    import subprocess,sys
    from scripts.run_phone_demo import demo_environment
    key=key_file(tmp_path)
    env=demo_environment(os.environ,tmp_path/'bad.sqlite3')
    env.update(WP_ENV='test',WP_ENABLE_TEST_PASSWORD_RESET='1',WP_ENABLE_TEST_RESET_QUEUE='1',
               WP_ENABLE_MAIL_QUEUE='1',WP_MAIL_QUEUE_KEYS_FILE=str(key))
    env.update(patch)
    result=subprocess.run([sys.executable,'-c','import backend.app'],env=env,
                          capture_output=True,text=True,timeout=20)
    assert result.returncode!=0
    assert 'TEST_RESET_QUEUE_CONFIGURATION_REJECTED' in result.stderr
    assert 'private-secret' not in result.stderr and str(key) not in result.stderr

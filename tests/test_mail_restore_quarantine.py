"""Restore real disposable backups, never replay historical delivery."""
from contextlib import closing
import hashlib
import sqlite3
import time

import pytest

from backend import reset_mail_queue as queue, reset_mail_keys
from scripts import encrypted_sqlite_snapshot as database_backup, mail_queue_key_backup as key_backup
from tests.test_reset_mail_queue import store, enqueue, connect, NOW
from tests.test_reset_mail_retention import terminal
from tests.test_queued_reset_http import keys_file, request
from tests.test_password_reset_http import register
from tests.test_purchase_record_http_restart import server
from tests.test_sqlite_recovery_rehearsal import purchase, key_path


def active_jobs(con,keys,now):
    with queue.transaction(con):first=queue.claim(con,now=now)
    with queue.transaction(con):
        second=queue.claim(con,now=now)
        assert queue.start(con,keys,second,now=now)
    assert first and second


@pytest.mark.parametrize('history',['accepted','uncertain','failed','expired'])
def test_quarantine_blocks_active_jobs_and_preserves_terminal_history(store,history):
    con,path,keys,_=store
    for _ in range(3):enqueue(store)
    active_jobs(con,keys,NOW)
    with queue.transaction(con):terminal(con,'history',state=history)
    old=con.execute("SELECT * FROM reset_mail_queue WHERE id='history'").fetchone()
    tokens=con.execute('SELECT * FROM password_reset_tokens ORDER BY token_hash').fetchall()
    with queue.transaction(con):assert queue.quarantine_restored(con)=={'quarantined':3}
    assert con.execute("SELECT * FROM reset_mail_queue WHERE id='history'").fetchone()==old
    rows=con.execute("SELECT * FROM reset_mail_queue WHERE id!='history'").fetchall()
    assert sorted(r['state'] for r in rows)==['expired','expired','uncertain']
    assert all(r['payload'] is None and r['owner'] is None and r['lease_until'] is None
        and r['started_at'] is None and r['result']=='RESTORE_QUARANTINED' for r in rows)
    assert sum(r['attempts'] for r in rows)==1
    assert con.execute('SELECT * FROM password_reset_tokens ORDER BY token_hash').fetchall()==tokens
    before=con.execute('SELECT * FROM reset_mail_queue ORDER BY id').fetchall()
    with queue.transaction(con):assert queue.quarantine_restored(con)=={'quarantined':0}
    assert con.execute('SELECT * FROM reset_mail_queue ORDER BY id').fetchall()==before
    assert queue.dispatch_once(lambda:connect(path),keys,lambda *a:pytest.fail('historical job cannot send'),
        clock=lambda:NOW+1)=='IDLE'


def test_caller_rollback_restores_queue_and_reset_tokens(store):
    con=store[0];enqueue(store)
    before=con.execute('SELECT * FROM reset_mail_queue').fetchall()
    with pytest.raises(RuntimeError):
        with queue.transaction(con):
            con.execute('DELETE FROM password_reset_tokens')
            assert queue.quarantine_restored(con)=={'quarantined':1}
            raise RuntimeError('synthetic rollback')
    assert con.execute('SELECT * FROM reset_mail_queue').fetchall()==before
    assert con.execute('SELECT COUNT(*) FROM password_reset_tokens').fetchone()[0]==1


def test_quarantine_requires_explicit_transaction(store):
    with pytest.raises(ValueError,match='^QUEUE_REQUIRES_TRANSACTION$'):
        queue.quarantine_restored(store[0])


def bundle(tmp_path,keys_file):
    for name in ('wrapping','archives','recovered-keys'):(tmp_path/name).mkdir(mode=0o700)
    source=tmp_path/'source.sqlite3'
    db_wrapper=tmp_path/'wrapping'/'database.backup-key'
    mail_wrapper=tmp_path/'wrapping'/'mail.json'
    db_archive=tmp_path/'archives'/'database.wpbackup'
    mail_archive=tmp_path/'archives'/'keys.mailkeybackup'
    database_backup.make_backup_key(db_wrapper);key_backup.init_backup_key(mail_wrapper)
    with server(source,queued_keys=keys_file) as client:
        purchase(client);register(client)
        for _ in range(3):request(client)
        with closing(connect(source)) as con:
            active_jobs(con,reset_mail_keys.load_keys(keys_file),int(time.time()))
        assert database_backup.encrypted_backup(source,key_path(source),db_wrapper,db_archive)['encrypted_backup']
        key_backup.backup(keys_file,mail_wrapper,mail_archive)
    return source,db_wrapper,db_archive,mail_wrapper,mail_archive


def test_joint_database_and_mail_key_restore_quarantines_history(tmp_path,keys_file):
    source,db_wrapper,db_archive,mail_wrapper,mail_archive=bundle(tmp_path,keys_file)
    before=hashlib.sha256(source.read_bytes()).digest()
    with closing(connect(source)) as con:
        source_jobs=con.execute('SELECT * FROM reset_mail_queue ORDER BY id').fetchall()
        source_orders=con.execute('SELECT * FROM orders ORDER BY id').fetchall()
        assert con.execute('SELECT COUNT(*) FROM sessions').fetchone()[0]>0
    restored=tmp_path/'restored-db';recovered=tmp_path/'recovered-keys'/'keys.json'
    assert database_backup.encrypted_restore(db_archive,db_wrapper,restored)['restored']
    assert key_backup.restore(mail_archive,mail_wrapper,recovered)=={'restored':True}
    keys=reset_mail_keys.load_keys(recovered)
    assert keys.decrypt(source_jobs[0]).recipient
    target=restored/'database.sqlite3'
    with closing(connect(target)) as con:
        assert con.execute('SELECT COUNT(*) FROM sessions').fetchone()[0]==0
        assert con.execute('SELECT COUNT(*) FROM password_reset_tokens').fetchone()[0]==0
        assert con.execute('SELECT * FROM orders ORDER BY id').fetchall()==source_orders
        rows=con.execute('SELECT * FROM reset_mail_queue').fetchall()
        assert sorted(r['state'] for r in rows)==['expired','expired','uncertain']
        assert all(r['payload'] is None and r['result']=='RESTORE_QUARANTINED' for r in rows)
        assert con.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
    assert queue.dispatch_once(lambda:connect(target),keys,lambda *a:pytest.fail('restore cannot send'),
        clock=lambda:int(time.time()))=='IDLE'
    assert hashlib.sha256(source.read_bytes()).digest()==before
    with closing(connect(source)) as con:
        assert con.execute('SELECT * FROM reset_mail_queue ORDER BY id').fetchall()==source_jobs


def test_restore_failure_during_quarantine_removes_partial_target(tmp_path,keys_file,monkeypatch):
    source,wrapper,archive,_,_=bundle(tmp_path,keys_file)
    before=hashlib.sha256(source.read_bytes()).digest()
    def fail(_):raise RuntimeError('synthetic quarantine failure')
    monkeypatch.setattr(queue,'quarantine_restored',fail)
    destination=tmp_path/'failed-restore'
    with pytest.raises(RuntimeError,match='synthetic quarantine failure'):
        database_backup.encrypted_restore(archive,wrapper,destination)
    assert not destination.exists() and hashlib.sha256(source.read_bytes()).digest()==before

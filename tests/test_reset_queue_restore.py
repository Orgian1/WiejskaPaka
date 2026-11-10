"""Offline restore quarantine: disposable backups and no external transport."""
from contextlib import closing
import sqlite3

import pytest

from backend import reset_mail_queue as queue
from backend.smtp_reset_transport import outcome
from tests.test_reset_mail_queue import store, connect, enqueue, NOW


@pytest.mark.parametrize('state',['queued','leased','started'])
def test_restored_copy_never_replays_historical_reset_after_quarantine(store,tmp_path,state):
    source,path,keys,_=store
    enqueue(store)
    if state!='queued':
        with queue.transaction(source):lease=queue.claim(source,now=NOW)
        if state=='started':
            with queue.transaction(source):assert queue.start(source,keys,lease,now=NOW)
    restored=tmp_path/'restored.sqlite3'
    with closing(connect(restored)) as target:
        source.backup(target)
        assert target.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        with queue.transaction(target):assert queue.quarantine_restored(target)==1
        with queue.transaction(target):assert queue.quarantine_restored(target)==0
        saved=target.execute('SELECT * FROM reset_mail_queue').fetchone()
        assert saved['state']=='uncertain' and saved['result']=='RESTORE_QUARANTINE'
        assert all(saved[k] is None for k in ('payload','owner','lease_until','started_at'))
        assert saved['attempts']==(1 if state=='started' else 0)
        # Queue quarantine does not claim to invalidate links or restore sessions.
        assert target.execute('SELECT COUNT(*) FROM password_reset_tokens').fetchone()[0]==1
    # Reopen the restored file, including after the old lease would expire.
    for now in (NOW,NOW+120,NOW+900):
        assert queue.dispatch_once(lambda:connect(restored),keys,
            lambda *args:pytest.fail('restored history must not send'),clock=lambda:now)=='IDLE'
    original=source.execute('SELECT * FROM reset_mail_queue').fetchone()
    assert original['payload'] is not None
    assert original['state']==('queued' if state=='queued' else 'leased')


def test_quarantine_is_transactional_and_preserves_terminal_history(store):
    con,path,keys,_=store
    enqueue(store)
    assert queue.dispatch_once(lambda:connect(path),keys,
        lambda *args:outcome('ACCEPTED',accepted=True),clock=lambda:NOW)=='ACCEPTED'
    accepted=dict(con.execute('SELECT * FROM reset_mail_queue').fetchone())
    enqueue(store)
    before=[dict(r) for r in con.execute('SELECT * FROM reset_mail_queue ORDER BY id')]
    with pytest.raises(RuntimeError):
        with queue.transaction(con):
            assert queue.quarantine_restored(con)==1
            raise RuntimeError('synthetic rollback')
    assert [dict(r) for r in con.execute('SELECT * FROM reset_mail_queue ORDER BY id')]==before
    with queue.transaction(con):assert queue.quarantine_restored(con)==1
    assert dict(con.execute('SELECT * FROM reset_mail_queue WHERE id=?',(accepted['id'],)).fetchone())==accepted


def test_quarantine_refuses_implicit_transaction(store):
    con,_,_,_=store
    enqueue(store)
    with pytest.raises(ValueError,match='QUEUE_REQUIRES_TRANSACTION'):
        queue.quarantine_restored(con)
    assert con.execute('SELECT state FROM reset_mail_queue').fetchone()[0]=='queued'

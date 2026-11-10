"""One persisted gate across both actual purchase and verification queues."""
from contextlib import closing
from concurrent.futures import ThreadPoolExecutor
from threading import Event
import time
import pytest
from backend import email_ownership as proof,email_verification_queue as verify,order_mail_outbox as orders
from backend.mail_send_budget import Gate,Policy,SCHEMA_SQLITE as BUDGET_SCHEMA
from backend.mail_suppression import SCHEMA_SQLITE as BLOCK_SCHEMA
SCHEMA_SQLITE=BUDGET_SCHEMA+BLOCK_SCHEMA
from backend.reset_mail_queue import KeyRing,transaction
from backend.smtp_reset_transport import outcome
from tests.test_order_mail_outbox import seed,store,add


def prepare(store):
    now=int(time.time())+2;keys=KeyRing({'test':b'z'*32},'test')
    with closing(store[0]()) as con:
        con.executescript(verify.SCHEMA_SQLITE+SCHEMA_SQLITE)
        with transaction(con):
            secret=proof.issue(con,store[2],now=now);assert proof.consume(con,store[2],secret,now=now)
            farmer=con.execute("SELECT id FROM users WHERE role='rolnik'").fetchone()['id']
            assert verify.enqueue(con,keys,farmer,now=now)
    add(store)
    return now,keys


def test_purchase_and_verification_share_inflight_lease_and_keep_deferred_job(store):
    now,keys=prepare(store);policy=Policy(1,10);entered=Event();release=Event()
    def submit(*args,**kwargs):
        entered.set();assert release.wait(10);return outcome('ACCEPTED',accepted=True)
    with ThreadPoolExecutor(max_workers=1) as pool:
        result=pool.submit(orders.dispatch_once,store[0],store[1],submit,proof.verified_recipient,
            clock=lambda:now,gate=Gate(policy,clock=lambda:now))
        try:
            assert entered.wait(10)
            assert verify.dispatch_once(store[0],keys,lambda *a:pytest.fail('Overlap'),now=now,
                gate=Gate(policy,clock=lambda:now))=='RATE_LIMITED'
            with closing(store[0]()) as con:
                row=con.execute('SELECT state,payload FROM email_verification_queue').fetchone()
                assert row['state']=='queued' and row['payload'] is not None
        finally:release.set()
        assert result.result(timeout=10)=='ACCEPTED'
    assert verify.dispatch_once(store[0],keys,lambda *a:outcome('ACCEPTED',accepted=True),now=now+1,
        gate=Gate(policy,clock=lambda:now+1))=='ACCEPTED'


@pytest.mark.parametrize('response',[outcome('REJECTED'),outcome('DELIVERY_UNCERTAIN')])
def test_rejection_or_uncertainty_consumes_capacity_without_retry(store,response):
    now,keys=prepare(store);policy=Policy(1,1)
    expected=response['status']
    assert orders.dispatch_once(store[0],store[1],lambda *a,**kw:response,proof.verified_recipient,
        clock=lambda:now,gate=Gate(policy,clock=lambda:now))==expected
    assert verify.dispatch_once(store[0],keys,lambda *a:pytest.fail('Quota exhausted'),now=now+1,
        gate=Gate(policy,clock=lambda:now+1))=='RATE_LIMITED'
    with closing(store[0]()) as con:
        assert con.execute('SELECT count(*) FROM mail_send_attempts').fetchone()[0]==1
        assert con.execute('SELECT state FROM email_verification_queue').fetchone()[0]=='queued'


def test_spawned_batch_stops_at_budget_without_consuming_queued_secret(store):
    from functools import partial
    from backend import email_verification_worker as worker
    from tests.test_email_verification_worker import connect,accepted
    now=int(time.time());policy=Policy(1,1);keys=KeyRing({'test':b'j'*32},'test')
    with closing(store[0]()) as con:
        path=con.execute('PRAGMA database_list').fetchone()['file']
        con.executescript(verify.SCHEMA_SQLITE+SCHEMA_SQLITE)
        with transaction(con):
            farmer=con.execute("SELECT id FROM users WHERE role='rolnik'").fetchone()['id']
            assert verify.enqueue(con,keys,farmer,now=now-1)
            gate=Gate(policy,clock=lambda:now-10)
            assert gate.claim(con,now-10);gate.finish(con)
    assert worker.run_process(partial(connect,path),keys,accepted,max_jobs=25,timeout_seconds=30,policy=policy)=={
        'status':'RATE_LIMITED','counts':{'RATE_LIMITED':1}}
    with closing(store[0]()) as con:
        row=con.execute('SELECT state,payload FROM email_verification_queue').fetchone()
        assert row['state']=='queued' and row['payload'] is not None


@pytest.mark.parametrize('used',[False,True])
def test_snapshot_restore_pauses_budget_and_preserves_attempt_history(store,seed,tmp_path,used):
    from pathlib import Path
    from scripts.sqlite_snapshot import snapshot
    from tests.test_sqlite_recovery_rehearsal import key_path
    with closing(store[0]()) as con:
        source=Path(con.execute('PRAGMA database_list').fetchone()['file'])
        con.executescript(SCHEMA_SQLITE)
        if used:
            with transaction(con):
                gate=Gate(Policy(1,10),clock=lambda:100)
                assert gate.claim(con,100);gate.finish(con)
    target=tmp_path/'budget-restored'
    snapshot(source,key_path(seed[0]),target,restore=True)
    import sqlite3
    with closing(sqlite3.connect(target/'database.sqlite3')) as con:
        assert con.execute('SELECT paused FROM mail_send_budget').fetchone()[0]==1
        assert con.execute('SELECT count(*) FROM mail_send_attempts').fetchone()[0]==int(used)
    with closing(store[0]()) as con:
        if used:assert con.execute('SELECT paused FROM mail_send_budget').fetchone()[0]==0
        else:assert con.execute('SELECT count(*) FROM mail_send_budget').fetchone()[0]==0


@pytest.mark.parametrize('reason',['permanent_bounce','complaint'])
def test_suppressed_recipients_never_reach_either_transport_or_consume_budget(store,reason):
    from backend import mail_suppression as blocks
    now,keys=prepare(store);policy=Policy(1,10)
    with closing(store[0]()) as con,transaction(con):
        for row in con.execute('SELECT email FROM users').fetchall():blocks.block(con,row['email'],reason,now=now)
    assert orders.dispatch_once(store[0],store[1],lambda *a,**kw:pytest.fail('Suppressed'),proof.verified_recipient,
        clock=lambda:now,gate=Gate(policy))=='SUPPRESSED'
    assert verify.dispatch_once(store[0],keys,lambda *a:pytest.fail('Suppressed'),now=now,gate=Gate(policy))=='SUPPRESSED'
    with closing(store[0]()) as con:
        assert con.execute('SELECT count(*) FROM mail_send_attempts').fetchone()[0]==0
        assert con.execute('SELECT state FROM order_mail_outbox').fetchone()[0]=='skipped'
        row=con.execute('SELECT state,payload FROM email_verification_queue').fetchone()
        assert row['state']=='expired' and row['payload'] is None

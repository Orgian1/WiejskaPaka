"""Disconnected queue tests: real SQLite transactions and synthetic secrets only."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
import sqlite3
import threading

from argon2 import PasswordHasher
import pytest

from backend import reset_mail_queue as queue, password_reset as reset
from backend.smtp_reset_transport import outcome

NOW=1792396800
EMAIL='queue-owner@example.invalid'


def connect(path):
    con=sqlite3.connect(path,timeout=10)
    con.row_factory=sqlite3.Row
    con.execute('PRAGMA foreign_keys=ON')
    return con


@pytest.fixture
def store(tmp_path):
    path=tmp_path/'queue.sqlite3';con=connect(path)
    con.executescript('''CREATE TABLE users(id INTEGER PRIMARY KEY,email TEXT,password_hash TEXT);
      CREATE TABLE sessions(token_hash TEXT,user_id INTEGER,expires_at TEXT);
      CREATE TABLE login_attempts(email TEXT PRIMARY KEY,failures INTEGER,locked_until TEXT);''')
    con.executescript(reset.SCHEMA_SQLITE);con.executescript(queue.SCHEMA)
    hasher=PasswordHasher(time_cost=1,memory_cost=1024,parallelism=1)
    con.execute('INSERT INTO users VALUES(1,?,?)',(EMAIL,hasher.hash('Old-synthetic-password!')));con.commit()
    keys=queue.KeyRing({'v1':b'a'*32},'v1')
    yield con,path,keys,hasher
    con.close()


def enqueue(store,now=NOW):
    con,_,keys,_=store
    with queue.transaction(con):return queue.issue(con,keys,EMAIL,now=now)


def leased(store,now=NOW):
    con,_,keys,_=store;enqueue(store,now)
    with queue.transaction(con):lease=queue.claim(con,now=now)
    return lease


def started(store,now=NOW):
    con,_,keys,_=store;lease=leased(store,now)
    with queue.transaction(con):delivery=queue.start(con,keys,lease,now=now)
    assert delivery
    return lease,delivery


def row(con):return con.execute('SELECT * FROM reset_mail_queue').fetchone()


def test_issue_encrypts_both_address_and_token_and_survives_reopen(store):
    con,path,keys,_=store;job=enqueue(store)
    saved=row(con);assert saved['id']==job
    assert EMAIL.encode() not in bytes(saved['payload'])
    con2=connect(path)
    try:
        with queue.transaction(con2):lease=queue.claim(con2,now=NOW)
        with queue.transaction(con2):delivery=queue.start(con2,keys,lease,now=NOW)
        assert delivery.recipient==EMAIL and len(delivery.token)==43
        assert delivery.token.encode() not in path.read_bytes()
        assert EMAIL not in repr(delivery) and delivery.token not in repr(delivery)
        assert lease.owner not in repr(lease)
        assert reset.digest(delivery.token)==saved['token_hash']
    finally:con2.close()


def test_unknown_account_and_budget_never_create_jobs(store):
    con,_,keys,_=store
    with queue.transaction(con):assert queue.issue(con,keys,'missing@example.invalid',now=NOW) is None
    assert con.execute('SELECT COUNT(*) FROM reset_mail_queue').fetchone()[0]==0
    assert con.execute('SELECT COUNT(*) FROM password_reset_tokens').fetchone()[0]==0
    for _ in range(3):assert enqueue(store)
    assert enqueue(store) is None
    assert con.execute('SELECT COUNT(*) FROM reset_mail_queue').fetchone()[0]==3


def test_queue_insert_failure_rolls_back_token_and_limits(store):
    con,_,keys,_=store
    con.execute("CREATE TRIGGER reject_queue BEFORE INSERT ON reset_mail_queue BEGIN SELECT RAISE(ABORT,'synthetic fault'); END");con.commit()
    with pytest.raises(sqlite3.IntegrityError):
        with queue.transaction(con):queue.issue(con,keys,EMAIL,now=NOW)
    for table in ('reset_mail_queue','password_reset_tokens','password_reset_limits'):
        assert con.execute('SELECT COUNT(*) FROM '+table).fetchone()[0]==0


def test_failure_after_queue_insert_rolls_back_everything(store):
    con,_,keys,_=store
    with pytest.raises(RuntimeError):
        with queue.transaction(con):
            queue.issue(con,keys,EMAIL,now=NOW)
            raise RuntimeError('synthetic failure before commit')
    for table in ('reset_mail_queue','password_reset_tokens','password_reset_limits'):
        assert con.execute('SELECT COUNT(*) FROM '+table).fetchone()[0]==0


def test_two_connections_only_one_worker_claims(store):
    con,path,_,_=store;enqueue(store);barrier=threading.Barrier(2)
    def work():
        c=connect(path)
        try:
            barrier.wait()
            with queue.transaction(c):return queue.claim(c,now=NOW)
        finally:c.close()
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(lambda _:work(),range(2)))
    assert sum(r is not None for r in results)==1
    assert row(con)['state']=='leased'


def test_unstarted_expired_lease_can_be_reclaimed_but_stale_owner_cannot_start(store):
    con,_,keys,_=store;old=leased(store)
    with queue.transaction(con):new=queue.claim(con,now=NOW+120)
    assert new.job_id==old.job_id and new.owner!=old.owner
    with queue.transaction(con):assert queue.start(con,keys,old,now=NOW+121) is None
    with queue.transaction(con):assert queue.start(con,keys,new,now=NOW+121)
    assert row(con)['attempts']==1


def test_crash_after_start_is_uncertain_and_payload_is_erased(store):
    con,path,_,_=store;lease,_=started(store)
    c=connect(path)
    try:
        with queue.transaction(c):assert queue.claim(c,now=NOW+120) is None
        assert row(c)['state']=='uncertain' and row(c)['payload'] is None
        with queue.transaction(c):assert not queue.finish(c,lease,outcome('ACCEPTED',accepted=True),now=NOW+121)
    finally:c.close()
    assert row(con)['state']=='uncertain'


@pytest.mark.parametrize('status,expected,accepted',[
 ('ACCEPTED','accepted',True),('DELIVERY_UNCERTAIN','uncertain',False),
 ('REJECTED','failed',False),('TLS_FAILED','failed',False),
 ('MESSAGE_REJECTED','failed',False),('DISABLED','failed',False)])
def test_terminal_results_never_requeue_and_purge_payload(store,status,expected,accepted):
    con,_,_,_=store;lease,_=started(store)
    with queue.transaction(con):assert queue.finish(con,lease,outcome(status,accepted=accepted),now=NOW+1)
    r=row(con);assert r['state']==expected and r['payload'] is None and r['owner'] is None
    with queue.transaction(con):assert queue.claim(con,now=NOW+500) is None


def test_transient_rejection_has_bounded_backoff_then_stops(store):
    con,_,keys,_=store;enqueue(store);now=NOW
    for attempt,delay in ((1,30),(2,60),(3,None)):
        with queue.transaction(con):lease=queue.claim(con,now=now)
        with queue.transaction(con):assert queue.start(con,keys,lease,now=now)
        with queue.transaction(con):assert queue.finish(con,lease,outcome('REJECTED',retryable=True),now=now)
        assert row(con)['attempts']==attempt
        if delay:
            assert row(con)['payload'] is not None
            with queue.transaction(con):assert queue.claim(con,now=now+delay-1) is None
            now+=delay
    assert row(con)['state']=='failed' and row(con)['payload'] is None


def test_no_retry_past_token_expiry(store):
    con,_,keys,_=store;lease=leased(store,NOW)
    with queue.transaction(con):lease=queue.claim(con,now=NOW+880)
    with queue.transaction(con):assert queue.start(con,keys,lease,now=NOW+880)
    with queue.transaction(con):queue.finish(con,lease,outcome('CONNECTION_FAILED',retryable=True),now=NOW+881)
    assert row(con)['state']=='failed'


@pytest.mark.parametrize('change',['password','delete_token','expired','future','recipient'])
def test_revalidate_token_account_and_clock_before_attempt(store,change):
    con,_,keys,_=store;lease=leased(store)
    if change=='password':con.execute("UPDATE users SET password_hash='changed'")
    elif change=='delete_token':con.execute('DELETE FROM password_reset_tokens')
    elif change=='recipient':con.execute("UPDATE users SET email='other@example.invalid'")
    elif change=='future':con.execute('UPDATE password_reset_tokens SET created_at=?',
                                    (datetime.fromtimestamp(NOW+1,timezone.utc).isoformat(),))
    else:con.execute('UPDATE password_reset_tokens SET expires_at=?',
                     (datetime.fromtimestamp(NOW,timezone.utc).isoformat(),))
    con.commit()
    with queue.transaction(con):assert queue.start(con,keys,lease,now=NOW) is None
    assert row(con)['state'] in ('expired','failed') and row(con)['payload'] is None
    assert row(con)['attempts']==0


@pytest.mark.parametrize('fault',['wrong_key','missing_version','ciphertext','metadata'])
def test_payload_authentication_fails_closed_without_secret_error(store,fault):
    con,_,keys,_=store;lease=leased(store)
    if fault=='wrong_key':keys=queue.KeyRing({'v1':b'z'*32},'v1')
    elif fault=='missing_version':keys=queue.KeyRing({'v2':b'z'*32},'v2')
    elif fault=='ciphertext':con.execute("UPDATE reset_mail_queue SET payload=x'00'")
    else:con.execute('UPDATE reset_mail_queue SET expires_at=expires_at+1')
    con.commit()
    with queue.transaction(con):assert queue.start(con,keys,lease,now=NOW) is None
    assert row(con)['state']=='failed' and row(con)['result']=='PAYLOAD_REJECTED'
    assert row(con)['payload'] is None


def test_key_rotation_keeps_old_payload_readable(store):
    con,_,_,_=store;lease=leased(store)
    keys=queue.KeyRing({'v1':b'a'*32,'v2':b'b'*32},'v2')
    with queue.transaction(con):assert queue.start(con,keys,lease,now=NOW)


def test_start_rollback_leaves_no_started_marker(store):
    con,_,keys,_=store;lease=leased(store)
    with pytest.raises(RuntimeError):
        with queue.transaction(con):
            assert queue.start(con,keys,lease,now=NOW)
            raise RuntimeError('simulated commit failure')
    assert row(con)['started_at'] is None and row(con)['attempts']==0
    with queue.transaction(con):assert queue.claim(con,now=NOW+120)


def test_result_without_start_or_with_wrong_owner_cannot_mutate(store):
    con,_,keys,_=store;lease=leased(store)
    with queue.transaction(con):assert not queue.finish(con,lease,outcome('ACCEPTED',accepted=True),now=NOW)
    with queue.transaction(con):assert queue.start(con,keys,lease,now=NOW)
    with queue.transaction(con):assert queue.start(con,keys,lease,now=NOW) is None
    wrong=queue.Lease(lease.job_id,'wrong-owner')
    with queue.transaction(con):assert not queue.finish(con,wrong,outcome('ACCEPTED',accepted=True),now=NOW)
    assert row(con)['state']=='leased'


@pytest.mark.parametrize('bad',[
 {},{'status':'ACCEPTED'},outcome('ACCEPTED'),outcome('DELIVERY_UNCERTAIN',retryable=True),
 outcome('TLS_FAILED',retryable=True),dict(outcome('ACCEPTED',accepted=True),delivery_confirmed=True)])
def test_invalid_adapter_outcomes_are_rejected(store,bad):
    con,_,_,_=store;lease,_=started(store)
    with pytest.raises(ValueError,match='QUEUE_INVALID_OUTCOME'):
        with queue.transaction(con):queue.finish(con,lease,bad,now=NOW)
    assert row(con)['state']=='leased'


def test_expiry_purges_unclaimed_ciphertext(store):
    con,_,_,_=store;enqueue(store)
    with queue.transaction(con):assert queue.claim(con,now=NOW+900) is None
    assert row(con)['state']=='expired' and row(con)['payload'] is None


def test_reset_consumption_invalidates_other_queued_links(store):
    con,_,keys,hasher=store;first=enqueue(store);enqueue(store)
    with queue.transaction(con):lease=queue.claim(con,now=NOW)
    with queue.transaction(con):delivery=queue.start(con,keys,lease,now=NOW)
    with queue.transaction(con):
        assert reset.consume(con,hasher,delivery.token,'New-synthetic-password!',
                             now=datetime.fromtimestamp(NOW,timezone.utc))==200
    with queue.transaction(con):queue.finish(con,lease,outcome('ACCEPTED',accepted=True),now=NOW)
    with queue.transaction(con):second=queue.claim(con,now=NOW)
    with queue.transaction(con):assert queue.start(con,keys,second,now=NOW) is None
    assert con.execute("SELECT COUNT(*) FROM reset_mail_queue WHERE state='expired'").fetchone()[0]==1


def test_transaction_is_required_and_nested_transactions_are_refused(store):
    con,_,keys,_=store
    with pytest.raises(ValueError):queue.issue(con,keys,EMAIL,now=NOW)
    with queue.transaction(con):
        with pytest.raises(ValueError):
            with queue.transaction(con):pass


@pytest.mark.parametrize('keys,active',[({},'v1'),({'v1':b'a'},'v1'),({'v1':b'a'*32},'missing'),({'bad key':b'a'*32},'bad key')])
def test_invalid_keys_fail_without_printing_key(keys,active):
    with pytest.raises(ValueError,match='^QUEUE_KEY_CONFIGURATION_REJECTED$'):queue.KeyRing(keys,active)


def test_dispatch_commits_started_marker_before_transport_and_holds_no_write_lock(store):
    con,path,keys,_=store;enqueue(store);calls=[]
    def transport(recipient,token):
        other=connect(path)
        try:
            assert row(other)['started_at']==NOW and row(other)['attempts']==1
            with queue.transaction(other):other.execute("UPDATE users SET email=email WHERE id=1")
        finally:other.close()
        calls.append((recipient,token));return outcome('ACCEPTED',accepted=True)
    assert queue.dispatch_once(lambda:connect(path),keys,transport,clock=lambda:NOW)=='ACCEPTED'
    assert len(calls)==1 and row(con)['state']=='accepted'
    assert queue.dispatch_once(lambda:connect(path),keys,transport,clock=lambda:NOW)=='IDLE'
    assert len(calls)==1


@pytest.mark.parametrize('bad',['exception','malformed'])
def test_dispatch_untrusted_transport_failure_is_uncertain_without_error_details(store,bad):
    con,path,keys,_=store;enqueue(store)
    def transport(recipient,token):
        if bad=='exception':raise RuntimeError('private provider error '+recipient+' '+token)
        return {'status':['private value']}
    assert queue.dispatch_once(lambda:connect(path),keys,transport,clock=lambda:NOW)=='DELIVERY_UNCERTAIN'
    assert row(con)['state']=='uncertain' and row(con)['payload'] is None
    assert row(con)['result']=='DELIVERY_UNCERTAIN'


def test_dispatch_does_not_send_when_start_commit_fails(store):
    con,path,keys,_=store;enqueue(store);calls=[]
    class FailStartCommit(sqlite3.Connection):
        commits=0
        def commit(self):
            self.commits+=1
            if self.commits==2:raise sqlite3.OperationalError('synthetic commit failure')
            super().commit()
    def factory():
        c=sqlite3.connect(path,factory=FailStartCommit);c.row_factory=sqlite3.Row;return c
    with pytest.raises(sqlite3.OperationalError):
        queue.dispatch_once(factory,keys,lambda *args:calls.append(args),clock=lambda:NOW)
    assert calls==[] and row(con)['started_at'] is None


def test_crash_after_smtp_acceptance_before_result_commit_never_causes_duplicate(store):
    con,path,keys,_=store;enqueue(store);calls=[]
    class FailResultCommit(sqlite3.Connection):
        commits=0
        def commit(self):
            self.commits+=1
            if self.commits==3:raise sqlite3.OperationalError('synthetic result commit failure')
            super().commit()
    def factory():
        c=sqlite3.connect(path,factory=FailResultCommit);c.row_factory=sqlite3.Row;return c
    def transport(*args):calls.append(True);return outcome('ACCEPTED',accepted=True)
    with pytest.raises(sqlite3.OperationalError):
        queue.dispatch_once(factory,keys,transport,clock=lambda:NOW)
    assert row(con)['state']=='leased' and row(con)['started_at']==NOW
    assert queue.dispatch_once(lambda:connect(path),keys,transport,clock=lambda:NOW+120)=='IDLE'
    assert calls==[True] and row(con)['state']=='uncertain'


def test_two_dispatchers_only_one_submission(store):
    con,path,keys,_=store;enqueue(store);barrier=threading.Barrier(2);calls=[]
    def run():
        barrier.wait()
        return queue.dispatch_once(lambda:connect(path),keys,
            lambda *args:(calls.append(True) or outcome('ACCEPTED',accepted=True)),clock=lambda:NOW)
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(lambda _:run(),range(2)))
    assert sorted(results)==['ACCEPTED','IDLE'] and calls==[True]


@pytest.mark.parametrize('failure,expected',[('quit','accepted'),('uncertain','uncertain'),('temporary','queued')])
def test_queue_and_existing_smtp_adapter_agree_on_delivery_state(store,failure,expected):
    import smtplib
    from backend import smtp_reset_transport as mail
    con,path,keys,_=store;enqueue(store);events=[]
    class Peer:
        def __init__(self,**kwargs):pass
        def __enter__(self):return self
        def __exit__(self,*args):
            if failure=='quit':raise smtplib.SMTPServerDisconnected('synthetic quit failure')
        def ehlo(self):events.append('ehlo');return 250,b'ok'
        def starttls(self,**kwargs):events.append('tls')
        def login(self,*args):events.append('auth')
        def send_message(self,message,**kwargs):
            events.append('send');assert kwargs['to_addrs']==[EMAIL]
            if failure=='uncertain':raise smtplib.SMTPServerDisconnected('synthetic DATA failure')
            if failure=='temporary':raise smtplib.SMTPDataError(451,b'synthetic refusal')
            return {}
    config=mail.SMTPConfig('smtp.example.invalid',587,'starttls','synthetic-user','synthetic-password',
                           'noreply@example.invalid','https://app.example.invalid')
    queue.dispatch_once(lambda:connect(path),keys,
        lambda recipient,token:mail.send_reset(config,recipient,token,factory=Peer),clock=lambda:NOW)
    assert row(con)['state']==expected and events==['ehlo','tls','ehlo','auth','send']


def test_expired_worker_result_is_not_recorded_and_is_recovered_conservatively(store):
    con,path,keys,_=store;enqueue(store);current=[NOW]
    def transport(*args):current[0]+=120;return outcome('ACCEPTED',accepted=True)
    assert queue.dispatch_once(lambda:connect(path),keys,transport,clock=lambda:current[0])=='STALE'
    with queue.transaction(con):queue.recover(con,now=current[0])
    assert row(con)['state']=='uncertain'

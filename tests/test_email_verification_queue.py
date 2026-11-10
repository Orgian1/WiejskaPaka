from contextlib import closing
import sqlite3
import pytest
from backend import email_verification_queue as queue, email_ownership as proof
from backend.reset_mail_queue import KeyRing, transaction
from backend.smtp_reset_transport import outcome


@pytest.fixture
def store(tmp_path):
    path=tmp_path/'mail.sqlite3'
    def connect():
        con=sqlite3.connect(path);con.row_factory=sqlite3.Row
        con.execute('PRAGMA foreign_keys=ON');return con
    with closing(connect()) as con:
        con.execute('CREATE TABLE users(id INTEGER PRIMARY KEY,email TEXT)')
        con.execute("INSERT INTO users VALUES(1,'buyer@example.invalid')")
        con.commit();con.executescript(queue.SCHEMA_SQLITE)
    return connect,KeyRing({'test':b'k'*32},'test')


def enqueue(store,now=100):
    with closing(store[0]()) as con,transaction(con):
        assert queue.enqueue(con,store[1],1,now=now)


def test_encrypted_delivery_once_with_durable_marker(store):
    connect,keys=store;enqueue(store);seen=[]
    with closing(connect()) as con:
        row=con.execute('SELECT * FROM email_verification_queue').fetchone()
        token=keys.decrypt(row).token
        assert token.encode() not in bytes(row['payload'])
        assert b'buyer@example.invalid' not in bytes(row['payload'])
    def send(recipient,secret):
        assert recipient=='buyer@example.invalid' and secret==token
        with closing(connect()) as con:
            row=con.execute('SELECT * FROM email_verification_queue').fetchone()
            assert row['state']=='started' and row['payload'] is None
        seen.append(secret);return outcome('ACCEPTED',accepted=True)
    assert queue.dispatch_once(connect,keys,send,now=101)=='ACCEPTED'
    assert queue.dispatch_once(connect,keys,send,now=102)=='IDLE'
    assert len(seen)==1


@pytest.mark.parametrize('kind',['expired','changed_address','already_verified','bad_key','replaced'])
def test_ineligible_or_superseded_link_is_not_sent(store,kind):
    connect,keys=store;enqueue(store)
    with closing(connect()) as con,transaction(con):
        if kind=='changed_address':con.execute("UPDATE users SET email='other@example.invalid'")
        if kind=='already_verified':
            row=con.execute('SELECT * FROM email_verification_queue').fetchone()
            assert proof.consume(con,1,keys.decrypt(row).token,now=101)
        if kind=='replaced':assert proof.issue(con,1,now=160)
    if kind=='bad_key':keys=KeyRing({'test':b'x'*32},'test')
    assert queue.dispatch_once(connect,keys,lambda *a:pytest.fail('Must not send'),now=1000 if kind=='expired' else 161)=='SKIPPED'


@pytest.mark.parametrize('result',[outcome('DELIVERY_UNCERTAIN'),None,{'status':'ACCEPTED'}])
def test_uncertain_attempts_are_not_retried(store,result):
    connect,keys=store;enqueue(store)
    assert queue.dispatch_once(connect,keys,lambda *a:result,now=101)=='UNCERTAIN'
    assert queue.dispatch_once(connect,keys,lambda *a:pytest.fail('Retry'),now=301)=='IDLE'


def test_crash_marker_and_restore_quarantine(store):
    connect,keys=store;enqueue(store)
    def crash(*args):raise KeyboardInterrupt()
    with pytest.raises(KeyboardInterrupt):queue.dispatch_once(connect,keys,crash,now=101)
    assert queue.dispatch_once(connect,keys,lambda *a:pytest.fail('Retry'),now=222)=='IDLE'
    with closing(connect()) as con,transaction(con):
        queue.quarantine_restored(con)
        assert con.execute('SELECT count(*) FROM account_email_proofs').fetchone()[0]==0
        assert con.execute('SELECT state FROM email_verification_queue').fetchone()[0]=='uncertain'


def test_persistent_account_budget_and_window(store):
    connect,_=store
    with closing(connect()) as con,transaction(con):
        assert all(queue.budget(con,1,'127.0.0.1','issue',now=100) for _ in range(5))
        assert not queue.budget(con,1,'different-peer','issue',now=101)
    with closing(connect()) as con,transaction(con):
        assert not queue.budget(con,1,'new-peer','issue',now=102)
        assert queue.budget(con,1,'127.0.0.1','issue',now=3700)


def test_reissue_replaces_queue_slot(store):
    enqueue(store);enqueue(store,160)
    with closing(store[0]()) as con:assert con.execute('SELECT count(*) FROM email_verification_queue').fetchone()[0]==1


def test_concurrent_workers_submit_one_message(store):
    from concurrent.futures import ThreadPoolExecutor
    connect,keys=store;enqueue(store);seen=[]
    def submit(*args):seen.append(True);return outcome('ACCEPTED',accepted=True)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(lambda _:queue.dispatch_once(connect,keys,submit,now=101),range(2)))
    assert sorted(results)==['ACCEPTED','IDLE'] and len(seen)==1


def test_ip_and_global_budgets_bound_other_accounts_and_bucket_growth(store):
    connect,_=store
    with closing(connect()) as con,transaction(con):
        for user_id in range(1,31):assert queue.budget(con,user_id,'same-peer','issue',now=100)
        assert not queue.budget(con,31,'same-peer','issue',now=100)
        con.execute("UPDATE email_verification_limits SET attempts=1000 WHERE bucket='issue:global'")
        count=con.execute('SELECT count(*) FROM email_verification_limits').fetchone()[0]
        assert not queue.budget(con,9999,'unique-peer','issue',now=100)
        assert con.execute('SELECT count(*) FROM email_verification_limits').fetchone()[0]==count

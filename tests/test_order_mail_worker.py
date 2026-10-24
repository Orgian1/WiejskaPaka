"""Spawned purchase confirmation worker; actual saved checkouts, no SMTP."""
from contextlib import closing
from functools import partial
import multiprocessing
import sqlite3
import time
import pytest
from backend import email_ownership as proof, order_mail_worker as worker
from backend.reset_mail_queue import transaction
from backend.smtp_reset_transport import outcome
from tests.test_order_mail_outbox import seed,store,add


def connect(path):
    con=sqlite3.connect(path);con.row_factory=sqlite3.Row;return con


def accepted(recipient,purchase,*,email_verified):
    assert email_verified is True and recipient=='klient@example.invalid'
    assert purchase.total_grosze==1149 and purchase.delivery_grosze==501
    assert len(purchase.pin)==6 and all(line[2]=='kg' for line in purchase.lines)
    print('synthetic-private-pin-and-recipient')
    return outcome('ACCEPTED',accepted=True)


def uncertain(*args,**kwargs):return outcome('DELIVERY_UNCERTAIN')


def forbidden(*args,**kwargs):raise AssertionError('Must not send')


def hang(*args,**kwargs):
    time.sleep(30)
    return outcome('ACCEPTED',accepted=True)


def prepare(store,*,verified=True):
    with closing(store[0]()) as con:
        path=con.execute('PRAGMA database_list').fetchone()['file']
        con.executescript(proof.SCHEMA_SQLITE)
        if verified:
            with transaction(con):
                now=int(time.time());token=proof.issue(con,store[2],now=now)
                assert proof.consume(con,store[2],token,now=now)
    add(store)
    return partial(connect,path)


def test_finite_purchase_worker_redacts_output_and_never_resends(store,capfd):
    factory=prepare(store)
    assert worker.run_process(factory,store[1],accepted,max_jobs=1,timeout_seconds=30)=={
        'status':'LIMIT_REACHED','counts':{'ACCEPTED':1}}
    assert worker.run_process(factory,store[1],forbidden,max_jobs=1,timeout_seconds=30)=={
        'status':'IDLE','counts':{'IDLE':1}}
    with closing(factory()) as con:
        assert con.execute('SELECT state FROM order_mail_outbox').fetchone()[0]=='accepted'
    assert 'synthetic-private' not in ''.join(capfd.readouterr())
    assert not multiprocessing.active_children()


@pytest.mark.parametrize('problem',['unverified','cancelled','changed_address','expired'])
def test_ineligible_purchases_are_skipped_before_transport(store,problem):
    factory=prepare(store,verified=problem!='unverified')
    with closing(factory()) as con,transaction(con):
        if problem=='cancelled':con.execute("UPDATE orders SET status='anulowane_testowo'")
        if problem=='changed_address':con.execute("UPDATE users SET email='other@example.invalid' WHERE id=?",(store[2],))
    if problem=='expired':
        assert worker.dispatch(factory,store[1],forbidden,clock=lambda:int(time.time())+7200)=='SKIPPED'
    else:
        assert worker.run_process(factory,store[1],forbidden,max_jobs=1,timeout_seconds=30)=={
            'status':'LIMIT_REACHED','counts':{'SKIPPED':1}}


def test_uncertain_purchase_submission_cannot_be_automatically_retried(store):
    factory=prepare(store)
    assert worker.run_process(factory,store[1],uncertain,max_jobs=1,timeout_seconds=30)=={
        'status':'LIMIT_REACHED','counts':{'DELIVERY_UNCERTAIN':1}}
    assert worker.run_process(factory,store[1],forbidden,max_jobs=1,timeout_seconds=30)=={
        'status':'IDLE','counts':{'IDLE':1}}


def test_purchase_deadline_has_no_fabricated_delivery_result(store):
    factory=prepare(store)
    assert worker.run_process(factory,store[1],hang,max_jobs=1,timeout_seconds=5)=={
        'status':'TIME_LIMIT','counts':None}
    with closing(factory()) as con:
        assert con.execute('SELECT state FROM order_mail_outbox').fetchone()[0] in ('queued','started')
    assert not multiprocessing.active_children()

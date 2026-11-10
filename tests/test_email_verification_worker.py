"""Spawned finite worker; synthetic transport only, never SES."""
from contextlib import closing
from functools import partial
import multiprocessing
import sqlite3
import time
import pytest
from backend import email_verification_queue as queue, email_verification_worker as worker
from backend.reset_mail_queue import transaction
from backend.smtp_reset_transport import outcome
from tests.test_email_verification_queue import store


def connect(path):
    con=sqlite3.connect(path);con.row_factory=sqlite3.Row
    return con


def accepted(recipient,token):
    print('synthetic-private-recipient-and-token')
    return outcome('ACCEPTED',accepted=True)


def uncertain(recipient,token):return outcome('DELIVERY_UNCERTAIN')


def hang(recipient,token):
    time.sleep(30)
    return outcome('ACCEPTED',accepted=True)


def seed(store,count=1):
    with closing(store[0]()) as con,transaction(con):
        path=con.execute('PRAGMA database_list').fetchone()['file']
        for user_id in range(1,count+1):
            if user_id>1:con.execute('INSERT INTO users VALUES(?,?)',(user_id,str(user_id)+'@example.invalid'))
            assert queue.enqueue(con,store[1],user_id,now=int(time.time()))
    return partial(connect,path)


def test_finite_batch_and_private_child_output(store,capfd):
    factory=seed(store,2)
    assert worker.run_process(factory,store[1],accepted,max_jobs=1,timeout_seconds=30)=={
        'status':'LIMIT_REACHED','counts':{'ACCEPTED':1}}
    with closing(factory()) as con:
        assert con.execute("SELECT count(*) FROM email_verification_queue WHERE state='accepted' AND payload IS NULL").fetchone()[0]==1
        assert con.execute("SELECT count(*) FROM email_verification_queue WHERE state='queued'").fetchone()[0]==1
    assert 'synthetic-private' not in ''.join(capfd.readouterr())
    assert not multiprocessing.active_children()


def test_uncertain_submission_never_retried_by_new_batch(store):
    factory=seed(store)
    assert worker.run_process(factory,store[1],uncertain,max_jobs=1,timeout_seconds=30)=={
        'status':'LIMIT_REACHED','counts':{'DELIVERY_UNCERTAIN':1}}
    assert worker.run_process(factory,store[1],accepted,max_jobs=1,timeout_seconds=30)=={
        'status':'IDLE','counts':{'IDLE':1}}


def test_deadline_terminates_child_without_requeueing_started_mail(store):
    factory=seed(store)
    assert worker.run_process(factory,store[1],hang,max_jobs=1,timeout_seconds=5)=={
        'status':'TIME_LIMIT','counts':None}
    with closing(factory()) as con:
        row=con.execute('SELECT * FROM email_verification_queue').fetchone()
        # Even on a slow host killed before startup, no speculative retry or
        # fabricated delivery result may occur. Started rows have no ciphertext.
        assert row['state'] in ('queued','started')
        if row['state']=='started':assert row['payload'] is None
    assert not multiprocessing.active_children()


@pytest.mark.parametrize('jobs,seconds',[(0,10),(26,10),(True,10),(1,0),(1,61)])
def test_invalid_limits_before_spawn(jobs,seconds):
    with pytest.raises(ValueError,match='LIMITS_REJECTED'):
        worker.run_process(None,None,None,max_jobs=jobs,timeout_seconds=seconds)

"""Spawned workers, disposable SQLite, synthetic callbacks; never SMTP."""
from functools import partial
import multiprocessing
import time

import pytest

from backend import reset_mail_queue as queue, reset_mail_worker as worker
from backend.smtp_reset_transport import outcome
from tests.test_reset_mail_queue import store, connect, enqueue


def accepted(recipient, token):
    print('synthetic-private-recipient-token-must-not-cross-worker-output')
    return outcome('ACCEPTED', accepted=True)


def hang(recipient, token):
    time.sleep(30)
    return outcome('ACCEPTED', accepted=True)


def cannot_connect():
    raise RuntimeError('synthetic-private-dsn-and-password')


def hang_before_connection():
    time.sleep(30)
    raise RuntimeError('unreachable')


def rejected(recipient, token):
    raise RuntimeError('synthetic-private-transport-error')


def seeded(store, count=1):
    now = int(time.time())
    for _ in range(count):
        enqueue(store, now=now)
    return partial(connect, store[1])


def test_spawned_batch_limits_tasks_and_suppresses_adapter_output(store, capfd):
    connect_db = seeded(store, 3)
    result = worker.run_process(connect_db, store[2], accepted, max_jobs=2, timeout_seconds=30)
    assert result == {'status':'LIMIT_REACHED', 'counts':{'ACCEPTED':2}}
    rows = store[0].execute('SELECT state,attempts,payload FROM reset_mail_queue').fetchall()
    assert sum(r['state']=='accepted' and r['payload'] is None for r in rows) == 2
    assert sum(r['state']=='queued' and r['attempts']==0 for r in rows) == 1
    assert 'synthetic-private' not in ''.join(capfd.readouterr())
    assert not multiprocessing.active_children()


def test_empty_worker_exits_and_does_not_sleep_or_create_rows(store):
    result = worker.run_process(partial(connect,store[1]),store[2],accepted,timeout_seconds=10)
    assert result == {'status':'IDLE','counts':{'IDLE':1}}
    assert store[0].execute('SELECT count(*) FROM reset_mail_queue').fetchone()[0] == 0


def test_deadline_after_start_preserves_uncertainty_without_resending(store):
    connect_db = seeded(store)
    result = worker.run_process(connect_db,store[2],hang,max_jobs=1,timeout_seconds=3)
    assert result == {'status':'TIME_LIMIT','counts':None}
    row = store[0].execute('SELECT * FROM reset_mail_queue').fetchone()
    assert row['state']=='leased' and row['started_at'] is not None and row['attempts']==1
    recovery_time = row['lease_until']+1
    with queue.transaction(store[0]):
        queue.recover(store[0],now=recovery_time)
    row = store[0].execute('SELECT * FROM reset_mail_queue').fetchone()
    assert row['state']=='uncertain' and row['payload'] is None
    assert queue.dispatch_once(connect_db,store[2],lambda *a:pytest.fail('must not resend'),
        clock=lambda:recovery_time)=='IDLE'
    assert not multiprocessing.active_children()


def test_deadline_before_connection_does_not_change_queued_job(store):
    seeded(store)
    assert worker.run_process(hang_before_connection,store[2],accepted,timeout_seconds=1) == {
        'status':'TIME_LIMIT','counts':None}
    row = store[0].execute('SELECT * FROM reset_mail_queue').fetchone()
    assert row['state']=='queued' and row['attempts']==0
    assert not multiprocessing.active_children()


def test_worker_failure_is_redacted_and_does_not_claim_delivery(store,capfd):
    assert worker.run_process(cannot_connect,store[2],accepted,timeout_seconds=10) == {
        'status':'WORKER_FAILED','counts':None}
    assert 'synthetic-private' not in ''.join(capfd.readouterr())


def test_transport_exception_is_recorded_as_uncertain(store,capfd):
    connect_db=seeded(store)
    result=worker.run_process(connect_db,store[2],rejected,max_jobs=1,timeout_seconds=10)
    assert result=={'status':'LIMIT_REACHED','counts':{'DELIVERY_UNCERTAIN':1}}
    assert store[0].execute('SELECT state,payload FROM reset_mail_queue').fetchone()[:] == ('uncertain',None)
    assert 'synthetic-private' not in ''.join(capfd.readouterr())


def test_stop_before_claim_has_no_database_or_transport_effect():
    stop=multiprocessing.get_context('spawn').Event();stop.set()
    result=worker.run_batch(lambda:pytest.fail('cannot connect'),None,
        lambda *a:pytest.fail('cannot send'),max_jobs=1,stop=stop)
    assert result=={'status':'STOPPED','counts':{}}


@pytest.mark.parametrize('jobs,seconds',[(0,1),(26,1),(True,1),(1,0),(1,61),(1,True)])
def test_invalid_limits_rejected_before_process_start(jobs,seconds):
    with pytest.raises(ValueError,match='^MAIL_WORKER_LIMITS_REJECTED$'):
        worker.run_process(None,None,None,max_jobs=jobs,timeout_seconds=seconds)


def test_unpicklable_configuration_returns_fixed_failure(store):
    result=worker.run_process(lambda:None,store[2],accepted,timeout_seconds=1)
    assert result=={'status':'WORKER_FAILED','counts':None}
    assert not multiprocessing.active_children()


@pytest.mark.parametrize('value',[{'status':'synthetic-private','counts':{}},
    {'status':'IDLE','counts':{'synthetic-private':1}},
    {'status':'LIMIT_REACHED','counts':{'ACCEPTED':True}},
    {'status':'LIMIT_REACHED','counts':{'ACCEPTED':26}},
    {'status':'IDLE','counts':{},'secret':'synthetic-private'}])
def test_only_allowlisted_results_cross_parent_boundary(value):
    assert worker._report(value,25)=={'status':'WORKER_FAILED','counts':None}

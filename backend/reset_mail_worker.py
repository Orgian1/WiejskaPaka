"""Explicit bounded child process; no environment, default DB, SMTP or daemon.

The caller supplies picklable connection and transport factories. Timeouts
never imply delivery failure or permit a retry: durable queue leases decide.
"""
from contextlib import redirect_stdout, redirect_stderr
import multiprocessing
import os
import time

from backend import reset_mail_queue as queue

STATUSES = frozenset({'IDLE', 'SKIPPED', 'STALE', 'ACCEPTED', 'DELIVERY_UNCERTAIN',
    'REJECTED', 'CONNECTION_FAILED', 'TLS_FAILED', 'MESSAGE_REJECTED', 'DISABLED'})


def _limits(max_jobs, timeout_seconds):
    if (type(max_jobs) is not int or not 1 <= max_jobs <= 25 or
            type(timeout_seconds) is not int or not 1 <= timeout_seconds <= 60):
        raise ValueError('MAIL_WORKER_LIMITS_REJECTED')


def run_batch(connect, keys, transport, *, max_jobs, stop, clock=time.time):
    """Cooperative batch; run_process additionally enforces a wall-clock limit."""
    _limits(max_jobs, 1)
    counts = {}
    for _ in range(max_jobs):
        if stop.is_set():
            return {'status': 'STOPPED', 'counts': counts}
        status = queue.dispatch_once(connect, keys, transport, clock=lambda: int(clock()))
        if status not in STATUSES:
            raise ValueError('MAIL_WORKER_RESULT_REJECTED')
        counts[status] = counts.get(status, 0) + 1
        if status == 'IDLE':
            return {'status': 'IDLE', 'counts': counts}
    return {'status': 'LIMIT_REACHED', 'counts': counts}


def _child(sender, stop, connect, keys, transport, max_jobs):
    # No adapter output, traceback, recipient, token or credential crosses IPC.
    with open(os.devnull, 'w') as sink, redirect_stdout(sink), redirect_stderr(sink):
        try:
            result = run_batch(connect, keys, transport, max_jobs=max_jobs, stop=stop)
        except Exception:
            result = {'status': 'WORKER_FAILED', 'counts': None}
        try:
            sender.send(result)
        finally:
            sender.close()


def _report(value, max_jobs):
    if not isinstance(value, dict) or set(value) != {'status', 'counts'}:
        return {'status': 'WORKER_FAILED', 'counts': None}
    if value['status'] == 'WORKER_FAILED' and value['counts'] is None:
        return value
    counts = value['counts']
    if (value['status'] not in {'STOPPED', 'IDLE', 'LIMIT_REACHED'} or
            not isinstance(counts, dict) or not set(counts) <= STATUSES or
            any(type(n) is not int or n < 1 for n in counts.values()) or
            sum(counts.values()) > max_jobs):
        return {'status': 'WORKER_FAILED', 'counts': None}
    return value


def run_process(connect, keys, transport, *, max_jobs=10, timeout_seconds=30):
    """Spawn a finite worker, terminate on deadline, return secret-free counts.

TIME_LIMIT/WORKER_FAILED deliberately return no counts: submission may have
started. Do not retry based on this report. Recover through the queue ledger.
This is process/time containment, not an OS privilege or network sandbox.
"""
    _limits(max_jobs, timeout_seconds)
    context = multiprocessing.get_context('spawn')
    receiver, sender = context.Pipe(duplex=False)
    stop = context.Event()
    child = context.Process(target=_child, args=(sender, stop, connect, keys, transport, max_jobs))
    started = False
    try:
        child.start()
        started = True
        sender.close()
        child.join(timeout_seconds)
        if child.is_alive():
            stop.set()
            child.join(1)
            return {'status': 'TIME_LIMIT', 'counts': None}
        if child.exitcode != 0 or not receiver.poll():
            return {'status': 'WORKER_FAILED', 'counts': None}
        return _report(receiver.recv(), max_jobs)
    except Exception:
        return {'status': 'WORKER_FAILED', 'counts': None}
    finally:
        if started and child.is_alive():
            child.terminate()
            child.join(2)
            if child.is_alive():
                child.kill()
                child.join(2)
        receiver.close()
        sender.close()
        if started and not child.is_alive():
            child.close()

"""Finite verification worker built on the shared spawned process boundary."""
from functools import partial
from backend.mail_send_budget import Gate
from backend import email_verification_queue as queue, reset_mail_worker as worker


def dispatch(connect,keys,transport,*,clock,policy=None):
    result=queue.dispatch_once(connect,keys,transport,now=int(clock()),gate=Gate(policy) if policy is not None else None)
    return {'UNCERTAIN':'DELIVERY_UNCERTAIN','FAILED':'REJECTED'}.get(result,result)


def run_process(connect,keys,transport,*,max_jobs=10,timeout_seconds=30,policy=None):
    return worker.run_process(connect,keys,transport,max_jobs=max_jobs,
                              timeout_seconds=timeout_seconds,dispatch=partial(dispatch,policy=policy))

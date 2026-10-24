"""Finite verification worker built on the shared spawned process boundary."""
from backend import email_verification_queue as queue, reset_mail_worker as worker


def dispatch(connect,keys,transport,*,clock):
    result=queue.dispatch_once(connect,keys,transport,now=int(clock()))
    return {'UNCERTAIN':'DELIVERY_UNCERTAIN','FAILED':'REJECTED'}.get(result,result)


def run_process(connect,keys,transport,*,max_jobs=10,timeout_seconds=30):
    return worker.run_process(connect,keys,transport,max_jobs=max_jobs,
                              timeout_seconds=timeout_seconds,dispatch=dispatch)

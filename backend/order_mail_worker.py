"""Finite purchase-mail process using proven account ownership and existing vault."""
from functools import partial
from backend.mail_send_budget import Gate
from backend import email_ownership as proof, order_mail_outbox as queue, reset_mail_worker as worker


def dispatch(connect,vault,transport,*,clock,policy=None):
    return queue.dispatch_once(connect,vault,transport,proof.verified_recipient,clock=clock,gate=Gate(policy) if policy is not None else None)


def run_process(connect,vault,transport,*,max_jobs=10,timeout_seconds=30,policy=None):
    return worker.run_process(connect,vault,transport,max_jobs=max_jobs,
                              timeout_seconds=timeout_seconds,dispatch=partial(dispatch,policy=policy))

"""Finite purchase-mail process using proven account ownership and existing vault."""
from backend import email_ownership as proof, order_mail_outbox as queue, reset_mail_worker as worker


def dispatch(connect,vault,transport,*,clock):
    return queue.dispatch_once(connect,vault,transport,proof.verified_recipient,clock=clock)


def run_process(connect,vault,transport,*,max_jobs=10,timeout_seconds=30):
    return worker.run_process(connect,vault,transport,max_jobs=max_jobs,
                              timeout_seconds=timeout_seconds,dispatch=dispatch)

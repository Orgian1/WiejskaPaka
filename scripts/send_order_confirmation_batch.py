"""Explicit finite SES purchase-mail batch; default invocation does no work.

python -m scripts.send_order_confirmation_batch --send --max-jobs 1
No API import, schema writes, implicit key creation, daemon or automatic retries.
"""
import argparse
from dataclasses import dataclass,field
import json
import os
from pathlib import Path
from backend import order_mail as mail, order_mail_worker as worker
from scripts.send_verification_batch import configured_connection

ROOT=Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Transport:
    config:object=field(repr=False)

    def __call__(self,recipient,purchase,*,email_verified):
        return mail.send_purchase(self.config,recipient,purchase,email_verified=email_verified)


def load_vault(environ,*,root=ROOT):
    try:
        from backend.checkout_vault import Vault,read_ring
        path=Path(environ['WP_CHECKOUT_KEY_FILE'])
        if os.name!='posix' or not path.is_absolute() or path.resolve().is_relative_to(Path(root).resolve()):
            raise ValueError('Existing private external POSIX checkout key required')
        return Vault(*read_ring(path))
    except Exception:raise ValueError('ORDER_WORKER_VAULT_REJECTED') from None


def execute(environ,*,send=False,max_jobs=1,timeout_seconds=30):
    if send is not True:return {'status':'DISABLED','counts':None}
    try:
        from backend.reset_mail_worker import _limits
        _limits(max_jobs,timeout_seconds)
        if any(environ.get(flag)!='1' for flag in (
                'WP_ENABLE_ORDER_MAIL_QUEUE','WP_ENABLE_EMAIL_VERIFICATION','WP_ENABLE_ORDER_SMTP')):
            raise ValueError('Explicit purchase-mail opt-ins required')
        connect=configured_connection(environ,required_tables=('account_email_proofs','order_mail_outbox'))
        vault=load_vault(environ)
        smtp=mail.load_ses_config(environ)
        if smtp is None:raise ValueError('Explicit purchase SMTP required')
        return worker.run_process(connect,vault,Transport(smtp),max_jobs=max_jobs,timeout_seconds=timeout_seconds)
    except Exception:return {'status':'WORKER_FAILED','counts':None}


def main(argv=None):
    parser=argparse.ArgumentParser(description='Finite, explicitly enabled SES purchase confirmations')
    parser.add_argument('--send',action='store_true')
    parser.add_argument('--max-jobs',type=int,default=1)
    parser.add_argument('--timeout-seconds',type=int,default=30)
    args=parser.parse_args(argv)
    result=execute(dict(os.environ),send=args.send,max_jobs=args.max_jobs,timeout_seconds=args.timeout_seconds)
    print(json.dumps(result,sort_keys=True))
    counts=result.get('counts') or {}
    return 1 if result['status'] in ('TIME_LIMIT','WORKER_FAILED') or any(
        key in counts for key in ('DELIVERY_UNCERTAIN','REJECTED','CONNECTION_FAILED','TLS_FAILED','MESSAGE_REJECTED','DISABLED')) else 0


if __name__=='__main__':raise SystemExit(main())

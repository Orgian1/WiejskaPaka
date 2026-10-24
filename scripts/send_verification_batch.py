"""Explicit SES verification batch. Never imports app, migrates, or starts a daemon.

Run as a module: python -m scripts.send_verification_batch --send --max-jobs 3
Without --send the command reads no secrets, connects nowhere and does no work.
"""
import argparse
from dataclasses import dataclass, field
import json
import os
from backend import email_verification_mail as mail, email_verification_worker as worker


@dataclass(frozen=True)
class Connect:
    dsn:str=field(repr=False)
    database_name:str
    required_tables:tuple=('account_email_proofs','email_verification_limits','email_verification_queue')

    def __call__(self):
        from backend.test_server_launcher import verify_test_database_connection
        from backend.pg_adapter import PgConnection
        from psycopg.rows import dict_row
        import psycopg
        # Read-only preflight runs inside the bounded child, including on every
        # fresh connection. No privileged application role or missing schema.
        verify_test_database_connection(self.dsn,self.database_name,require_schema=True,
            required_tables=self.required_tables)
        return PgConnection(psycopg.connect(self.dsn,row_factory=dict_row,connect_timeout=5))


@dataclass(frozen=True)
class Transport:
    config:object=field(repr=False)

    def __call__(self,recipient,token):return mail.send(self.config,recipient,token)


def configured_connection(environ,*,required_tables=None):
    from backend.test_server_launcher import prepare_test_server
    settings=prepare_test_server(environ)
    # Prevent inherited libpq settings from silently changing the validated target.
    if any(environ.get(k) for k in ('PGHOST','PGHOSTADDR','PGPORT','PGDATABASE','PGUSER',
            'PGPASSWORD','PGSERVICE','PGSERVICEFILE','PGOPTIONS')):
        raise ValueError('Inherited database routing rejected')
    options={} if required_tables is None else {'required_tables':required_tables}
    return Connect(environ['WP_TEST_DATABASE_URL'],settings['database_name'],**options)


def execute(environ,*,send=False,max_jobs=3,timeout_seconds=30):
    """Return fixed counts only. Any exception may follow uncertain submission."""
    if send is not True:return {'status':'DISABLED','counts':None}
    try:
        from backend.reset_mail_worker import _limits
        _limits(max_jobs,timeout_seconds)
        if (environ.get('WP_ENABLE_EMAIL_VERIFICATION')!='1' or
                environ.get('WP_ENABLE_VERIFICATION_SMTP')!='1'):
            raise ValueError('Explicit verification opt-ins required')
        connect=configured_connection(environ)
        from backend.reset_mail_keys import load_config as load_keys
        keys=load_keys(environ)
        smtp=mail.load_config(environ)
        if keys is None or smtp is None:raise ValueError('Explicit private keys and SMTP required')
        result=worker.run_process(connect,
            keys,Transport(smtp),max_jobs=max_jobs,timeout_seconds=timeout_seconds)
        return result
    except Exception:return {'status':'WORKER_FAILED','counts':None}


def main(argv=None):
    parser=argparse.ArgumentParser(description='Finite, explicitly enabled SES verification batch')
    parser.add_argument('--send',action='store_true')
    parser.add_argument('--max-jobs',type=int,default=3)
    parser.add_argument('--timeout-seconds',type=int,default=30)
    args=parser.parse_args(argv)
    result=execute(dict(os.environ),send=args.send,max_jobs=args.max_jobs,timeout_seconds=args.timeout_seconds)
    print(json.dumps(result,sort_keys=True))
    counts=result.get('counts') or {}
    return 1 if result['status'] in ('TIME_LIMIT','WORKER_FAILED') or any(
        key in counts for key in ('DELIVERY_UNCERTAIN','REJECTED','CONNECTION_FAILED','TLS_FAILED','MESSAGE_REJECTED','DISABLED')) else 0


if __name__=='__main__':raise SystemExit(main())

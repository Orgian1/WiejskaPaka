"""Explicit read-only local PostgreSQL wallet audit, no app import or listener."""
import argparse
import json
import os


def check(env=None,*,enabled=False):
    if not enabled:return {'status':'DISABLED'}
    try:
        env=dict(os.environ if env is None else env)
        from scripts.postgres_test_backup import local_parameters
        from backend.test_server_launcher import prepare_test_server
        from backend.pg_adapter import PgConnection
        from backend.wallet_integrity import inspect_wallets
        prepare_test_server(env)
        params=local_parameters(env['WP_TEST_DATABASE_URL'])
        params['options']='-c statement_timeout=10000 -c lock_timeout=1000 -c default_transaction_read_only=on -c search_path=pg_catalog,public,pg_temp'
        import psycopg
        from psycopg.rows import dict_row
        with psycopg.connect(**params,connect_timeout=5,row_factory=dict_row) as raw:
            role=raw.execute('SELECT rolsuper,rolbypassrls,rolcreatedb,rolcreaterole FROM pg_roles WHERE rolname=current_user').fetchone()
            if not role or any(role.values()):raise ValueError('Unprivileged application role required')
            result=inspect_wallets(PgConnection(raw))
        return {'status':'WALLETS_VALID' if result['success'] else 'WALLETS_INCONSISTENT',**result}
    except Exception:return {'status':'WALLET_CHECK_REJECTED','success':False}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check',action='store_true')
    args=parser.parse_args(argv)
    result=check(enabled=args.check)
    print(json.dumps(result,sort_keys=True))
    return int(result.get('success') is False)


if __name__=='__main__':raise SystemExit(main())

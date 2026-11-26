"""Run API and adversarial tests in a new LOCAL PostgreSQL cluster with RLS ON.

Requires requirements-security-test.txt. Never reads a production DSN, modifies
an existing cluster, deploys a migration, or contacts a VPS.
"""
import argparse
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import tempfile


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report',default='work/rls-api.xml')
    parser.add_argument('--legacy', action='store_true', help='Run the native API suite without RLS')
    parser.add_argument('--logs', type=Path, help='Local diagnostics from the disposable API')
    parser.add_argument('--select',default=None,help='Optional pytest -k expression for diagnostics')
    args=parser.parse_args(argv)
    import pgserver,psycopg
    from pgserver._commands import POSTGRES_BIN_PATH
    root=Path(__file__).resolve().parents[1]
    sys.path.insert(0,str(root))
    report=Path(args.report).resolve();report.parent.mkdir(parents=True,exist_ok=True)
    if args.logs:
        args.logs.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='wp-rls-api-') as folder:
        data=Path(folder)/'data'
        pgserver.initdb(['-A','trust','-U','security_admin'],pgdata=data)
        with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
        # The gate uses TCP DSNs only. Do not require Unix-domain sockets:
        # managed environments may allow loopback TCP while denying AF_UNIX.
        pgserver.pg_ctl(['-w','-l',str(Path(folder)/'pg.log'),'-o',f"-h 127.0.0.1 -p {port} -k ''",'start'],pgdata=data)
        try:
            dsn=f'postgresql://security_admin:disposable-local-only@127.0.0.1:{port}/wp_test_rls_gate'
            with psycopg.connect(dsn.replace('/wp_test_rls_gate','/postgres'),autocommit=True) as c:c.execute('CREATE DATABASE wp_test_rls_gate')
            key=Path(folder)/'capability.key';key.write_text(json.dumps({'key':secrets.token_hex(32)}));key.chmod(0o600)
            from scripts.run_tests_isolated import test_environment
            env=test_environment(os.environ,Path(folder)/'unused.sqlite3')
            env.update(WP_ENV='test', WP_TEST_POSTGRES_DSN=dsn, WP_TEST_DATABASE_URL=dsn,
                       PATH=str(POSTGRES_BIN_PATH)+os.pathsep+os.environ['PATH'])
            for variable in ('WP_TEST_ENABLE_RLS', 'WP_RLS_GATEWAY', 'WP_RLS_KEY_FILE',
                             'WP_TEST_POSTGRES_LOG_DIR'):
                env.pop(variable, None)
            if args.logs:
                env['WP_TEST_POSTGRES_LOG_DIR'] = str(args.logs.resolve())
            tests = ['tests/test_postgres_full_api_optin.py', 'tests/test_approved_demo_postgres.py', 'tests/test_incubator_invoicing.py']
            if args.legacy:
                tests += ['tests/test_postgres_environment.py',
                          'tests/test_postgres_transaction_integration_optional.py']
            else:
                env.update(WP_TEST_ENABLE_RLS='1', WP_RLS_KEY_FILE=str(key))
                tests += ['tests/test_postgres_rls_isolation_live.py']
            command = [sys.executable, '-m', 'pytest', '-q', '--tb=short', *tests, f'--junitxml={report}']
            if args.select:command.extend(['-k',args.select])
            return subprocess.run(command,cwd=root,env=env).returncode
        finally:pgserver.pg_ctl(['-w','stop'],pgdata=data)


if __name__=='__main__':raise SystemExit(main())

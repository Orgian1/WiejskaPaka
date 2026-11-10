"""Fail-closed preflight for a *new, empty, disposable* PostgreSQL test database.

Read-only. Never executes schema changes. Invoke before any psql migration.
"""
import os
from backend.test_server_preflight import check_test_server


def validate_target(environ=None, connect=None):
    env = dict(os.environ if environ is None else environ)
    settings = check_test_server(env)
    dsn = env['WP_TEST_DATABASE_URL']
    if connect is None:
        import psycopg
        connect = psycopg.connect
    con = connect(dsn, connect_timeout=5)
    try:
        with con.cursor() as cur:
            cur.execute('SET TRANSACTION READ ONLY')
            cur.execute('SELECT current_database(), current_user')
            identity = cur.fetchone()
            if not identity or identity[0] != settings['database_name']:
                raise ValueError('Wrong test database')
            cur.execute('SELECT rolsuper, rolbypassrls, rolcreaterole, rolcreatedb FROM pg_roles WHERE rolname = current_user')
            role = cur.fetchone()
            if role is None or len(role) != 4 or any(flag is not False for flag in role):
                raise ValueError('Privileged database role forbidden')
            cur.execute("SELECT count(*) FROM pg_catalog.pg_class c JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname NOT IN ('pg_catalog', 'information_schema') AND n.nspname NOT LIKE 'pg_toast%' AND n.nspname NOT LIKE 'pg_temp_%' AND c.relkind IN ('r','p','v','m','f','S')")
            count = cur.fetchone()
            if count is None or count[0] != 0:
                raise ValueError('Test database contains user objects')
        return {'ok': True, 'database': settings['database_name'], 'empty': True}
    finally:
        con.close()


def main():
    try:
        validate_target()
    except Exception:
        print('BLOCKED: test PostgreSQL target did not pass private empty-database preflight')
        return 1
    print('OK: disposable test database preflight passed (read-only)')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

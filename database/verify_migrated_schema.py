"""Read-only verification of the minimum API startup schema after test migrations."""
import os
from backend.test_server_preflight import check_test_server
from backend.postgres_schema_preflight import CORE_TABLES

STARTUP_COLUMNS = {
    'inventory_reservations': {'order_id', 'expires_at', 'released_at'},
    'order_purchase_records': {'order_id'},
    'pickup_point_coordinates': {'point_id'},
}


def verify_schema(environ=None, connect=None):
    env = dict(os.environ if environ is None else environ)
    settings = check_test_server(env)
    if connect is None:
        import psycopg
        connect = psycopg.connect
    con = connect(env['WP_TEST_DATABASE_URL'], connect_timeout=5)
    try:
        with con.cursor() as cur:
            # Fail closed: all subsequent probes run inside a read-only transaction.
            cur.execute('SET TRANSACTION READ ONLY')
            cur.execute('SELECT current_database()')
            identity = cur.fetchone()
            if not identity or identity[0] != settings['database_name']:
                raise ValueError('Unexpected PostgreSQL database')
            cur.execute('SELECT rolsuper, rolbypassrls, rolcreaterole, rolcreatedb FROM pg_roles WHERE rolname = current_user')
            role = cur.fetchone()
            if not role or len(role) != 4 or any(value is not False for value in role):
                raise ValueError('Privileged PostgreSQL role forbidden')
            cur.execute('SELECT table_name, column_name FROM information_schema.columns WHERE table_schema = %s AND table_name = ANY(%s)', ('public', list(CORE_TABLES)))
            rows = cur.fetchall()
        columns = {}
        for table, column in rows:
            columns.setdefault(table, set()).add(column)
        missing_tables = sorted(set(CORE_TABLES) - columns.keys())
        missing_columns = {table: sorted(required - columns.get(table, set())) for table, required in STARTUP_COLUMNS.items() if required - columns.get(table, set())}
        if missing_tables or missing_columns:
            raise ValueError('Incomplete PostgreSQL startup schema')
        return {'ok': True, 'checked_tables': len(CORE_TABLES), 'checked_startup_columns': sum(map(len, STARTUP_COLUMNS.values())), 'execution_performed': False}
    finally:
        con.close()


def main():
    try:
        report = verify_schema()
    except Exception:
        print('BLOCKED: PostgreSQL schema verification failed; no credentials disclosed')
        return 1
    print(f"OK: {report['checked_tables']} tables and {report['checked_startup_columns']} startup columns verified")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

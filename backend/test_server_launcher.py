"""Explicit private-test entrypoint; validate all settings before importing the API."""
import os

from backend.test_server_preflight import check_test_server

OPTIONAL_PREVIEW_TABLES = {
    'WP_ENABLE_PRODUCT_UNITS': ('product_sale_units', 'order_sale_units'),
    'WP_ENABLE_ADDRESS_DELIVERY': ('seller_delivery_windows', 'address_delivery_requests'),
    'WP_ENABLE_USER_PHOTOS': ('user_photos',),
    'WP_ENABLE_SELLER_SEARCH': ('seller_public_logins',),
    'WP_ENABLE_EMAIL_VERIFICATION': ('account_email_proofs', 'email_verification_limits', 'email_verification_queue'),
    'WP_ENABLE_ORDER_MAIL_QUEUE': ('order_mail_outbox',),
    'WP_ENABLE_ORDER_SMTP': ('order_mail_outbox','mail_send_budget','mail_send_attempts','mail_recipient_blocks'),
    'WP_ENABLE_VERIFICATION_SMTP': ('mail_send_budget','mail_send_attempts','mail_recipient_blocks'),
}


def required_preview_tables(environ):
    return tuple(table for flag, tables in OPTIONAL_PREVIEW_TABLES.items()
                 if environ.get(flag) == '1' for table in tables)


def prepare_test_server(environ=None):
    env = dict(os.environ if environ is None else environ)
    settings = check_test_server(env)
    if env.get('DATABASE_URL') and env['DATABASE_URL'] != env['WP_TEST_DATABASE_URL']:
        raise ValueError('DATABASE_URL must match dedicated WP_TEST_DATABASE_URL')
    if env.get('WIEJSKAPAKA_DB'):
        raise ValueError('SQLite WIEJSKAPAKA_DB must not be configured on PostgreSQL test server')
    raw_port = env.get('WP_PORT', '8000')
    if not isinstance(raw_port, str) or not raw_port.isascii() or not raw_port.isdecimal():
        raise ValueError('WP_PORT must be a decimal integer between 1 and 65535')
    port = int(raw_port)
    if not 1 <= port <= 65535:
        raise ValueError('WP_PORT must be between 1 and 65535')
    return {**settings, 'port': port}


def main():
    settings = prepare_test_server()
    # The API reads DATABASE_URL at import time; use the validated test DSN.
    test_dsn = os.environ['WP_TEST_DATABASE_URL']
    try:
        verify_test_database_connection(test_dsn, settings['database_name'], require_schema=True,
                                        required_tables=required_preview_tables(os.environ))
    except Exception:
        # Drivers may include credentials, hosts and DSNs in their error text.
        # Keep the private test launcher fail-closed without exposing them.
        raise RuntimeError('Test PostgreSQL preflight failed; inspect database configuration securely') from None
    # Do not publish an unverified DSN into process configuration.
    previous_dsn = os.environ.get('DATABASE_URL')
    had_dsn = 'DATABASE_URL' in os.environ
    try:
        os.environ['DATABASE_URL'] = test_dsn
        import uvicorn
        uvicorn.run('backend.app:app', host=settings['bind_host'], port=settings['port'],
                    reload=False, workers=1)
    finally:
        # Do not leave a database credential in the process after shutdown or
        # a failed server startup (important for embedded/test invocations).
        if had_dsn:
            os.environ['DATABASE_URL'] = previous_dsn
        else:
            os.environ.pop('DATABASE_URL', None)


def verify_test_database_connection(dsn, expected_name, connect=None, *, require_schema=False,
                                    required_tables=()):
    """Verify the actual PostgreSQL target before starting the HTTP listener.

    This only performs a read-only probe; it never creates or migrates a database.
    """
    if connect is None:
        import psycopg
        connect = psycopg.connect
    connection = connect(dsn, connect_timeout=5)
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT current_database()')
            row = cursor.fetchone()
        actual_name = row[0] if row else None
        if actual_name != expected_name:
            raise ValueError('Connected PostgreSQL database does not match validated test database')
        if require_schema:
            # Never run a shared test HTTP service with a PostgreSQL role that
            # can bypass row-level security or administer the database.
            with connection.cursor() as cursor:
                cursor.execute(
                    'SELECT rolsuper, rolbypassrls, rolcreaterole, rolcreatedb '
                    'FROM pg_roles WHERE rolname = current_user'
                )
                role = cursor.fetchone()
            if role is None or len(role) != 4 or any(flag is not False for flag in role):
                raise RuntimeError('Test PostgreSQL role must be non-privileged and cannot bypass RLS')
            from backend.postgres_schema_preflight import CORE_TABLES
            tables = tuple(dict.fromkeys((*CORE_TABLES, *required_tables)))
            with connection.cursor() as cursor:
                cursor.execute(
                    'SELECT table_name FROM information_schema.tables '
                    'WHERE table_schema = %s AND table_type = %s AND table_name = ANY(%s)',
                    ('public', 'BASE TABLE', list(tables)),
                )
                rows = cursor.fetchall()
            present = {row[0] for row in rows}
            missing = sorted(set(tables) - present)
            if missing:
                raise RuntimeError('Test PostgreSQL schema incomplete; missing tables: ' + ', '.join(missing))
    finally:
        connection.close()


if __name__ == '__main__':
    main()

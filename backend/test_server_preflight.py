"""Fail-closed checks before starting a private test server.

This module does not connect to any database or payment service.
"""
import ipaddress
import re
from urllib.parse import urlsplit, parse_qsl

from backend.deployment_guard import assert_safe_environment


def check_test_server(environ):
    """Return safe settings or raise before the application starts."""
    assert_safe_environment(environ)
    if environ.get('WP_ENV', '').strip().lower() not in {'test', 'testing'}:
        raise ValueError('Test server requires WP_ENV=test')
    if environ.get('WP_REAL_PAYMENTS', '').strip().lower() not in {'', '0', 'false', 'off', 'no'}:
        raise ValueError('Real payments must be disabled on test server')
    # The private listener must never create or migrate a database at API import.
    # Provision the test schema separately with an audited migration process.
    if 'WP_AUTO_INIT_POSTGRES' in environ:
        raise ValueError('WP_AUTO_INIT_POSTGRES must be unset on private test server')
    if environ.get('WP_PSP_SECRET') or environ.get('STRIPE_SECRET_KEY'):
        raise ValueError('Live/payment secrets must not be injected into test server')
    host = environ.get('WP_BIND_HOST', '127.0.0.1').strip()
    try:
        address = ipaddress.ip_address(host)
    except ValueError as exc:
        raise ValueError('Use an explicit loopback bind address') from exc
    if not address.is_loopback:
        raise ValueError('Test server must bind only to loopback; use authenticated tunnel')
    dsn = environ.get('WP_TEST_DATABASE_URL', '').strip()
    if not dsn:
        raise ValueError('Dedicated test PostgreSQL URL is required')
    parsed = urlsplit(dsn)
    if parsed.scheme not in {'postgresql', 'postgres'} or not parsed.hostname or not parsed.path.strip('/'):
        raise ValueError('Invalid test PostgreSQL URL')
    if parsed.fragment:
        raise ValueError('PostgreSQL URL must not contain a fragment')
    try:
        db_port = parsed.port
    except ValueError as exc:
        raise ValueError('Invalid PostgreSQL port') from exc
    if db_port is not None and not 1 <= db_port <= 65535:
        raise ValueError('Invalid PostgreSQL port')
    query_pairs = parse_qsl(parsed.query, keep_blank_values=True)
    # libpq supports numerous parameters (including newly introduced ones)
    # capable of changing connection routing or execution behavior.  Accept
    # only explicitly audited, non-routing options; reject unknown options.
    allowed_query_keys = {'sslmode', 'connect_timeout', 'application_name'}
    query_keys = [key.lower() for key, _ in query_pairs]
    if any(key not in allowed_query_keys for key in query_keys):
        raise ValueError('PostgreSQL URL contains an unsupported connection option')
    if len(query_keys) != len(set(query_keys)):
        raise ValueError('PostgreSQL URL contains duplicate connection options')
    for key, value in query_pairs:
        if key.lower() == 'connect_timeout' and (
            not value.isascii() or not value.isdecimal() or not 1 <= int(value) <= 30
        ):
            raise ValueError('PostgreSQL connection timeout must be 1–30 seconds')
        if key.lower() == 'application_name' and (
            not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]{0,62}', value, flags=re.ASCII)
        ):
            raise ValueError('Invalid PostgreSQL application name')
    ssl_modes = [value.lower() for key, value in query_pairs if key.lower() == 'sslmode']
    if len(ssl_modes) > 1:
        raise ValueError('Ambiguous PostgreSQL sslmode')
    try:
        db_host = ipaddress.ip_address(parsed.hostname)
        local_db = db_host.is_loopback
    except ValueError:
        local_db = parsed.hostname.lower() == 'localhost'
    if not local_db and ssl_modes != ['verify-full']:
        raise ValueError('Remote test PostgreSQL requires sslmode=verify-full')
    # Restrict to a single unescaped PostgreSQL database identifier.  Encoded
    # separators, query-like fragments and production aliases must not bypass
    # the dedicated-test-database gate.
    database_name = parsed.path[1:] if parsed.path.startswith('/') else ''
    if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]{0,62}', database_name, flags=re.ASCII):
        raise ValueError('Dedicated database name must be a simple SQL identifier')
    if database_name.lower() in {'postgres', 'production', 'prod', 'wiejskapaka', 'template0', 'template1'}:
        raise ValueError('Dedicated non-production database name required')
    return {'bind_host': host, 'database_name': database_name}

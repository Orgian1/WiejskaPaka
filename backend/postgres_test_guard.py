"""Conservative preflight for destructive PostgreSQL integration tests.

This only prevents accidental mistakes; it is not an authorization boundary.
"""
import os
from urllib.parse import parse_qs, unquote, urlsplit


class UnsafeTestDatabase(ValueError):
    pass


def require_disposable_postgres(dsn, *, environ=None):
    """Allow an explicitly named disposable DB on localhost or opted-in remote.

    Refuse ambiguous libpq connection strings, query overrides and multi-host
    addresses rather than trying to predict the driver's effective target.
    """
    env = os.environ if environ is None else environ
    try:
        parsed = urlsplit(dsn)
        if parsed.scheme not in ('postgres', 'postgresql'):
            raise ValueError('scheme')
        if parsed.fragment or not parsed.netloc or not parsed.hostname:
            raise ValueError('invalid host')
        # libpq accepts comma-separated hosts, but urlsplit does not reliably
        # identify their effective destination. Reject instead of guessing.
        if ',' in parsed.netloc or '%' in parsed.netloc:
            raise ValueError('ambiguous host')
        if parsed.username is None or parsed.password is None:
            raise ValueError('credentials required')
        if parsed.path.count('/') != 1:
            raise ValueError('ambiguous database path')
        dbname = unquote(parsed.path[1:])
        if not dbname or '/' in dbname or '\\' in dbname or '\x00' in dbname:
            raise ValueError('invalid database name')
        query = parse_qs(parsed.query, keep_blank_values=True)
        # libpq parameters may override the destination or redirect through
        # a service definition; only known non-routing options are permitted.
        if set(query) - {'sslmode', 'connect_timeout', 'application_name'}:
            raise ValueError('unsupported connection parameters')
        if len(query.get('sslmode', [])) > 1:
            raise ValueError('duplicate options')
        host = parsed.hostname.lower()
        _ = parsed.port  # force validation of malformed port
    except (ValueError, TypeError, AttributeError) as exc:
        raise UnsafeTestDatabase('Nieprawidłowy lub niejednoznaczny DSN PostgreSQL') from exc
    if not (dbname.endswith('_test') or dbname.startswith('wp_test_')):
        raise UnsafeTestDatabase('Baza musi mieć nazwę *_test lub wp_test_*')
    if host not in ('localhost', '127.0.0.1', '::1'):
        if env.get('WP_ALLOW_REMOTE_DISPOSABLE_TEST_DB') != 'YES_I_CONFIRM':
            raise UnsafeTestDatabase('Zdalna baza wymaga osobnego potwierdzenia środowiska testowego')
    return True

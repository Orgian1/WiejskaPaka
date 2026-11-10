"""Read-only local PostgreSQL preview probe; no server, migrations or payments."""
import json
import os
from pathlib import Path
import sys
from urllib.parse import urlsplit
import ipaddress

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.test_server_launcher import (prepare_test_server, verify_test_database_connection,
                                         required_preview_tables, OPTIONAL_PREVIEW_TABLES)
from backend.checkout_vault import read_ring


def inspect_preview(environ=None, *, connect=None):
    env = dict(os.environ if environ is None else environ)
    result = {'configuration_checked': False, 'checkout_key_checked': False,
              'database_core_checked': False, 'success': False,
              'database_optional_checked': False,
              'enabled_optional_features': [],
              'ready_for_production': False, 'preview_started': False,
              'backup_restore_verified': False}
    stage = 'CONFIGURATION_REJECTED'
    try:
        settings = prepare_test_server(env)
        host = urlsplit(env['WP_TEST_DATABASE_URL']).hostname
        try:
            local = ipaddress.ip_address(host).is_loopback
        except ValueError:
            local = host == 'localhost'
        if not local:
            raise ValueError('Probe accepts local PostgreSQL only')
        result['configuration_checked'] = True
        result['enabled_optional_features'] = [flag for flag in OPTIONAL_PREVIEW_TABLES
                                                if env.get(flag) == '1']
        stage = 'CHECKOUT_KEY_REJECTED'
        key = Path(env.get('WP_CHECKOUT_KEY_FILE', ''))
        if not key.is_absolute() or key.resolve().is_relative_to(ROOT):
            raise ValueError('Separate absolute key path required')
        read_ring(key)
        result['checkout_key_checked'] = True
        stage = 'DATABASE_PROBE_FAILED'
        if connect is None:
            import psycopg
            connect = psycopg.connect

        def readonly_connection(dsn, **kwargs):
            # Explicit options override inherited PGOPTIONS. This connection
            # performs no writes even if another probe is added accidentally.
            return connect(dsn, **kwargs, options=(
                '-c default_transaction_read_only=on -c statement_timeout=5000 '
                '-c lock_timeout=1000 -c search_path=pg_catalog'))

        verify_test_database_connection(env['WP_TEST_DATABASE_URL'],
            settings['database_name'], connect=readonly_connection, require_schema=True,
            required_tables=required_preview_tables(env))
        result['database_core_checked'] = True
        result['database_optional_checked'] = bool(result['enabled_optional_features'])
        result['success'] = True
    except Exception:
        # Exception messages may contain DSNs, key paths or driver credentials.
        result['error'] = stage
    return result


def main():
    result = inspect_preview()
    print(json.dumps(result, ensure_ascii=True, sort_keys=True))
    return 0 if result['success'] else 1


if __name__ == '__main__':
    raise SystemExit(main())

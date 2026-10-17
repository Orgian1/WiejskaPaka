"""Opt-in read-only PostgreSQL security inspection. Never prints DATABASE_URL."""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.postgres_security_preflight import inspect_security


def main():
    if os.environ.get('WP_READONLY_PG_PREFLIGHT') != 'YES_I_CONFIRM':
        raise SystemExit('Kontrola wymaga WP_READONLY_PG_PREFLIGHT=YES_I_CONFIRM')
    dsn = os.environ.get('DATABASE_URL', '').strip()
    if not dsn:
        raise SystemExit('Brak DATABASE_URL (nie przesyłaj hasła do czatu)')
    import psycopg
    with psycopg.connect(dsn, connect_timeout=5) as connection:
        # Read-only transaction prevents accidental writes, even if code changes.
        connection.execute('SET TRANSACTION READ ONLY')
        report = inspect_security(connection)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if report['findings']:
        raise SystemExit(2)


if __name__ == '__main__':
    main()

"""Uruchamia testy SQLite na nowej bazie; nigdy nie dotyka Neon.

Uwaga: dla całej regresji użyj run_full_regression.py, który izoluje
każdy moduł. Ten skrypt izoluje bazę tylko na poziomie całego procesu.

Użycie: python scripts/run_tests_isolated.py [-q] [tests/...]
"""
import os
from pathlib import Path
import subprocess
import sys
import tempfile


def test_environment(source, db_path):
    """Tworzy środowisko procesu potomnego bez połączenia produkcyjnego."""
    env = dict(source)
    # Nie pozwalamy, by DATABASE_URL przekierował testy na PostgreSQL/Neon.
    for key in (
        'WP_ENABLE_QUEUED_PASSWORD_RESET', 'WP_ENABLE_MAIL_QUEUE', 'WP_MAIL_QUEUE_KEYS_FILE',
        'DATABASE_URL', 'NEON_DATABASE_URL', 'WP_CHECKOUT_KEY_FILE',
        'WP_ENABLE_TEST_PASSWORD_RESET', 'WP_ENABLE_PG_TEST_PASSWORD_RESET', 'WP_TEST_RESET_OUTBOX',
        'WP_TEST_POSTGRES_DSN', 'WP_TEST_DATABASE_URL',
        'WP_ALLOW_REMOTE_DISPOSABLE_TEST_DB', 'WP_AUTO_INIT_POSTGRES',
        'PGHOST', 'PGHOSTADDR', 'PGPORT', 'PGDATABASE', 'PGUSER', 'PGPASSWORD',
        'PGPASSFILE', 'PGSERVICE', 'PGSERVICEFILE', 'PGOPTIONS', 'PGSSLCERT', 'PGSSLKEY',
    ):
        env.pop(key, None)
    env['WIEJSKAPAKA_DB'] = str(db_path)
    # Python children and captured pytest diagnostics must agree on Windows too.
    env['PYTHONUTF8'] = '1'
    env['PYTHONIOENCODING'] = 'utf-8'
    return env


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or not any(a.startswith("tests/") or a.startswith("test_") for a in args):
        print("UWAGA: wspólna baza dla wszystkich modułów może powodować konflikty ",
              "(np. test_b1141_isolation_probe_a/b). Do pełnej regresji użyj ",
              "scripts/run_full_regression.py.", flush=True)
    root = Path(__file__).resolve().parents[1]
    # Baza tworzona wyłącznie w katalogu tymczasowym i sprzątana po zakończeniu.
    with tempfile.TemporaryDirectory(prefix='wiejskapaka_pytest_') as tmp:
        database = Path(tmp) / 'tests.sqlite3'
        cmd = [sys.executable, '-m', 'pytest', *(args or ['-q'])]
        print('Testy na nowej, odizolowanej bazie SQLite (bez Neon).', flush=True)
        return subprocess.call(cmd, cwd=root, env=test_environment(os.environ, database))


if __name__ == '__main__':
    raise SystemExit(main())

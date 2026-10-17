"""Uruchom lokalny podgląd WiejskaPaka na 127.0.0.1, na jednorazowej SQLite.

Użycie: python scripts/run_phone_demo.py [--port 8765]
Podgląd jest dostępny wyłącznie na urządzeniu uruchamiającym skrypt.
"""
import argparse
import os
from pathlib import Path
import subprocess
import sys
import tempfile

SENSITIVE_DATABASE_KEYS = (
    'DATABASE_URL', 'WP_TEST_DATABASE_URL', 'WP_TEST_POSTGRES_DSN', 'WP_CHECKOUT_KEY_FILE',
    'WP_ALLOW_REMOTE_DISPOSABLE_TEST_DB',
)


def demo_environment(source, database):
    """Nie przekazuj do serwera demonstracyjnego konfiguracji PostgreSQL."""
    env = dict(source)
    for key in SENSITIVE_DATABASE_KEYS:
        env.pop(key, None)
    env['WIEJSKAPAKA_DB'] = str(database)
    # Demo nie może odziedziczyć przypadkowego trybu produkcyjnego.
    env['WIEJSKAPAKA_ENV'] = 'development'
    env['WP_ENV'] = 'development'
    return env


def main(argv=None):
    parser = argparse.ArgumentParser(description='Lokalny podgląd WiejskaPaka (bez prawdziwych płatności)')
    parser.add_argument('--port', type=int, default=8765)
    args = parser.parse_args(argv)
    if not 1024 <= args.port <= 65535:
        parser.error('Port musi być w zakresie 1024–65535')
    root = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix='wiejskapaka_phone_demo_') as directory:
        env = demo_environment(os.environ, Path(directory) / 'demo.sqlite3')
        command = [sys.executable, '-m', 'uvicorn', 'backend.app:app',
                   '--host', '127.0.0.1', '--port', str(args.port), '--no-access-log']
        print(f'WiejskaPaka DEMO: http://127.0.0.1:{args.port}', flush=True)
        print('Tylko na tym urządzeniu; brak Neon i prawdziwych płatności. Ctrl+C kończy demo.', flush=True)
        try:
            return subprocess.call(command, cwd=root, env=env)
        except KeyboardInterrupt:
            return 130


if __name__ == '__main__':
    raise SystemExit(main())

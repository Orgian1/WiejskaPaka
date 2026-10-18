"""Uruchom lokalny podgląd WiejskaPaka na 127.0.0.1, na jednorazowej SQLite.

Użycie: python scripts/run_phone_demo.py [--port 8765]
Podgląd jest dostępny wyłącznie na urządzeniu uruchamiającym skrypt.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

SENSITIVE_DATABASE_KEYS = (
    'NEON_DATABASE_URL', 'WP_ENABLE_TEST_PAYMENTS', 'DATABASE_URL', 'WP_TEST_DATABASE_URL', 'WP_TEST_POSTGRES_DSN', 'WP_CHECKOUT_KEY_FILE',
    'WP_ALLOW_REMOTE_DISPOSABLE_TEST_DB', 'WP_ENABLE_TEST_PASSWORD_RESET', 'WP_TEST_RESET_OUTBOX',
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
    parser.add_argument('--sample-data', action='store_true', help='Nowe fikcyjne konta wszystkich ról, produkty i przesyłki')
    args = parser.parse_args(argv)
    if not 1024 <= args.port <= 65535:
        parser.error('Port musi być w zakresie 1024–65535')
    root = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix='wiejskapaka_phone_demo_') as directory:
        database = Path(directory) / 'demo.sqlite3'
        credentials = None
        if args.sample_data:
            sample = Path(directory) / 'sample'
            try:
                setup = subprocess.run([sys.executable, '-m', 'scripts.prepare_sample_demo',
                    '--directory', str(sample)], cwd=root,
                    env=demo_environment(os.environ, sample/'demo.sqlite3'),
                    capture_output=True, text=True, encoding='utf-8', timeout=120)
            except (OSError, subprocess.TimeoutExpired):
                print('Przygotowanie demo przerwane lub niedostępne.', file=sys.stderr)
                return 1
            if setup.returncode != 0:
                print('Nie udało się przygotować przykładowego demo.', file=sys.stderr)
                return 1
            try:
                result = json.loads(setup.stdout)
                database = sample/'demo.sqlite3'
                if result['database'] != str(database):
                    raise ValueError('Nieprawidłowa baza demo')
                credentials = result['credentials']
                if set(credentials) != {'klient', 'rolnik', 'dostawca', 'admin'}:
                    raise ValueError('Niekompletne konta demo')
                for account in credentials.values():
                    if not isinstance(account['email'], str) or not account['email'].endswith('@example.invalid') or not isinstance(account['password'], str) or len(account['password']) < 24:
                        raise ValueError('Nieprawidłowe konto demo')
            except (ValueError, KeyError, TypeError):
                print('Nieprawidłowy wynik przygotowania demo.', file=sys.stderr)
                return 1
        env = demo_environment(os.environ, database)
        if args.sample_data:
            env['WP_ENABLE_TEST_PAYMENTS'] = '1'
        env['WP_ENABLE_TEST_PASSWORD_RESET'] = '1'
        env['WP_TEST_RESET_OUTBOX'] = str(Path(directory) / 'reset-mailbox')
        command = [sys.executable, '-m', 'uvicorn', 'backend.app:app',
                   '--host', '127.0.0.1', '--port', str(args.port), '--no-access-log']
        print(f'WiejskaPaka DEMO: http://127.0.0.1:{args.port}', flush=True)
        print('Skrzynka testowa odzyskiwania hasła: '+env['WP_TEST_RESET_OUTBOX'], flush=True)
        if credentials:
            print('Jednorazowe konta demo — nie udostępniaj tego okna ani haseł:', flush=True)
            for role in ('klient', 'rolnik', 'dostawca', 'admin'):
                account = credentials[role]
                print(f"{role}: {account['email']} | hasło: {account['password']}", flush=True)
            print('Przygotowano 2 produkty, przesyłkę do odbioru i dostawę w drodze. Płatności są symulowane.', flush=True)
        print('Tylko na tym urządzeniu; brak Neon i prawdziwych płatności. Ctrl+C kończy demo.', flush=True)
        try:
            return subprocess.call(command, cwd=root, env=env)
        except KeyboardInterrupt:
            return 130


if __name__ == '__main__':
    raise SystemExit(main())

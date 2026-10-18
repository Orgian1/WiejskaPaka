"""Uruchom lokalny podgląd WiejskaPaka na 127.0.0.1, na jednorazowej SQLite.

Użycie: python scripts/run_phone_demo.py [--port 8765]
Podgląd jest dostępny wyłącznie na urządzeniu uruchamiającym skrypt.
"""
import argparse
from contextlib import contextmanager, nullcontext
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


@contextmanager
def private_credentials_file(path, credentials):
    """Exclusive POSIX file; remove only the same file created by this process."""
    if os.name != 'posix':
        raise ValueError('Prywatny plik kont wymaga systemu POSIX')
    path = Path(path)
    parent = path.parent.lstat()
    if path.parent.is_symlink() or not path.parent.is_dir() or parent.st_uid != os.getuid() or parent.st_mode & 0o077:
        raise ValueError('Plik kont wymaga prywatnego katalogu bieżącego użytkownika')
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    identity = os.fstat(descriptor)
    try:
        with os.fdopen(descriptor, 'w', encoding='utf-8') as output:
            json.dump(credentials, output, ensure_ascii=True)
            output.write('\n')
        yield
    finally:
        try:
            current = path.lstat()
            if (current.st_dev, current.st_ino) == (identity.st_dev, identity.st_ino):
                path.unlink()
        except FileNotFoundError:
            pass


def main(argv=None):
    parser = argparse.ArgumentParser(description='Lokalny podgląd WiejskaPaka (bez prawdziwych płatności)')
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--sample-data', action='store_true', help='Nowe fikcyjne konta wszystkich ról, produkty i przesyłki')
    parser.add_argument('--credentials-file', type=Path, help='Prywatny, nowy plik kont zamiast haseł w terminalu (POSIX, wymaga --sample-data)')
    args = parser.parse_args(argv)
    if args.credentials_file and not args.sample_data:
        parser.error('--credentials-file wymaga --sample-data')
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
        try:
            private_output = private_credentials_file(args.credentials_file, credentials) if args.credentials_file else nullcontext()
            with private_output:
                if credentials:
                    if args.credentials_file:
                        print('Konta demo zapisano w prywatnym pliku; plik zostanie usunięty po zakończeniu podglądu.', flush=True)
                    else:
                        print('Jednorazowe konta demo — nie udostępniaj tego okna ani haseł:', flush=True)
                        for role in ('klient', 'rolnik', 'dostawca', 'admin'):
                            account = credentials[role]
                            print(f"{role}: {account['email']} | hasło: {account['password']}", flush=True)
                    print('Przygotowano 2 produkty, przesyłkę do odbioru i dostawę w drodze. Płatności są symulowane.', flush=True)
                print('Tylko na tym urządzeniu; brak Neon i prawdziwych płatności. Ctrl+C kończy demo.', flush=True)
                return subprocess.call(command, cwd=root, env=env)
        except KeyboardInterrupt:
            return 130
        except (OSError, ValueError):
            print('Nie można uruchomić podglądu lub utworzyć prywatnego pliku kont. Wymagany nowy plik w prywatnym katalogu POSIX.', file=sys.stderr)
            return 1



if __name__ == '__main__':
    raise SystemExit(main())

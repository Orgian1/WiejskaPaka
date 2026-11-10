"""Fail-closed deployment guard for the unfinished developer build."""
import os

PRODUCTION_VALUES = frozenset({'production', 'prod', 'live'})

def assert_safe_environment(environ=None):
    env = os.environ if environ is None else environ
    mode = env.get('WP_ENV', 'development').strip().lower()
    if mode in PRODUCTION_VALUES:
        raise RuntimeError(
            'WiejskaPaka: produkcyjne uruchomienie jest zablokowane. '
            'Wymagane testy PostgreSQL, audyt bezpieczeństwa, obsługa PSP i weryfikacja prawna.'
        )
    if mode not in ('development', 'dev', 'test', 'testing'):
        raise RuntimeError('WiejskaPaka: nieznany WP_ENV; dozwolone development/test.')
    return mode

"""Explicit test-only HTTP integration; never creates keys or starts delivery."""
from backend import password_reset, reset_mail_keys


def load_config(environ, database_url):
    if environ.get('WP_ENABLE_QUEUED_PASSWORD_RESET') != '1':
        return None
    try:
        if environ.get('WP_ENV', '').lower() not in ('test', 'testing'):
            raise ValueError('test environment required')
        if database_url and not password_reset.postgres_demo_reset_allowed(environ, database_url):
            raise ValueError('dedicated local database required')
        if environ.get('WP_ENABLE_TEST_PASSWORD_RESET') == '1':
            raise ValueError('choose one reset delivery mode')
        keys = reset_mail_keys.load_config(environ)
        if keys is None:
            raise ValueError('explicit private keys required')
        return keys
    except Exception:
        raise ValueError('RESET_HTTP_CONFIGURATION_REJECTED') from None

"""Private test HTTP queue configuration; no worker or transport startup."""
from backend.reset_mail_keys import load_config
from backend.password_reset import postgres_demo_reset_allowed


def load_test_queue_keys(environ, dsn, *, reset_enabled):
    """Return keys only for a fully explicit, non-filebox test configuration."""
    if environ.get('WP_ENABLE_TEST_RESET_QUEUE')!='1':return None
    try:
        if (not reset_enabled or environ.get('WP_ENV','').lower() not in ('test','testing')
                or environ.get('WP_TEST_RESET_OUTBOX')):
            raise ValueError('private queue test only')
        if dsn and not postgres_demo_reset_allowed(environ,dsn):
            raise ValueError('dedicated local PostgreSQL test required')
        keys=load_config(environ)
        if keys is None:raise ValueError('explicit key configuration required')
        return keys
    except Exception:
        raise ValueError('TEST_RESET_QUEUE_CONFIGURATION_REJECTED') from None

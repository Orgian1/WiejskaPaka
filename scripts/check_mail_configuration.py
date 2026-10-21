"""Read-only local mail configuration check; never connects or starts a worker.

Run as the intended service user: python -m scripts.check_mail_configuration
Supply configuration privately. Output contains fixed status codes only.
"""
import json
import os
from pathlib import Path

from backend import reset_mail_keys, smtp_reset_transport

ROOT = Path(__file__).resolve().parents[1]


def check(environ=None, *, root=ROOT):
    env = dict(os.environ if environ is None else environ)
    result = {}
    for name, flag, loader in (
        ('smtp', 'WP_ENABLE_SMTP', smtp_reset_transport.load_config),
        ('queue_keys', 'WP_ENABLE_MAIL_QUEUE', reset_mail_keys.load_config),
    ):
        if env.get(flag) != '1':
            result[name] = 'DISABLED'
            continue
        try:
            value = loader(env, root=root)
            result[name] = 'VALID' if value is not None else 'REJECTED'
        except Exception:
            # No exception message, path, mailbox, key or credential is published.
            result[name] = 'REJECTED'
    result['ready_for_connection_test'] = all(value == 'VALID' for value in result.values())
    result['network_checked'] = False
    result['delivery_checked'] = False
    return result


def main():
    result = check()
    print(json.dumps(result, sort_keys=True))
    return 0 if result['ready_for_connection_test'] else 1


if __name__ == '__main__':
    raise SystemExit(main())

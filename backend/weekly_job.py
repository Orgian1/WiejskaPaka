"""One-shot weekly payout preparation for an external cron/systemd timer.

No bank transfers or payment-provider calls. Disabled unless explicitly opted in.
"""
import argparse
import os
from datetime import datetime
from zoneinfo import ZoneInfo

from backend.payout_scheduler import prepare_weekly_run

WARSAW = ZoneInfo('Europe/Warsaw')


def execute(con, *, now=None, enabled=False):
    """Run a Monday batch in a serialized transaction. Caller commits/rolls back."""
    if not enabled:
        raise PermissionError('Harmonogram testowy jest wyłączony')
    now = now or datetime.now(WARSAW)
    if now.tzinfo is None:
        raise ValueError('Wymagana data ze strefą czasową')
    local = now.astimezone(WARSAW)
    if local.weekday() != 0:
        return {'status': 'skipped_not_monday', 'date': local.date().isoformat(), 'transfer_executed': False}
    # SQLite serializes writers via BEGIN IMMEDIATE. PostgreSQL locks the
    # stable advisory key across concurrent workers for the transaction.
    if os.environ.get('DATABASE_URL', '').strip():
        con.execute('SELECT pg_advisory_xact_lock(?)', (291029,))
    else:
        con.execute('BEGIN IMMEDIATE')
    result = prepare_weekly_run(con, local.date().isoformat(), local.isoformat())
    return {'status': 'already_prepared' if result['already_prepared'] else 'prepared', **result}


def main(argv=None):
    parser = argparse.ArgumentParser(description='Testowy poniedziałkowy przebieg WiejskaPaka')
    parser.add_argument('--run', action='store_true', help='Wymagane jawne zezwolenie na uruchomienie')
    args = parser.parse_args(argv)
    if not args.run or os.environ.get('WP_ENABLE_TEST_PAYMENTS') != '1' or os.environ.get('WP_ENABLE_WEEKLY_JOB') != '1':
        parser.error('Wymagane --run, WP_ENABLE_TEST_PAYMENTS=1 i WP_ENABLE_WEEKLY_JOB=1')
    # Import after opt-in to avoid initializing databases on a disabled invocation.
    from backend.app import db
    with db() as con:
        result = execute(con, enabled=True)
    print(result)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

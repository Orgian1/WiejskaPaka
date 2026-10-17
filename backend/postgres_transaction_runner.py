"""Retry an entire DB transaction using a fresh connection per attempt.

Only use for database-only, idempotent work. Never include network payments,
messages, or other external side effects in `operation`.
"""
from contextlib import closing
from math import isfinite
from time import sleep

from backend.postgres_retry_policy import should_retry_transaction


def run_transaction(connect, operation, *, max_attempts=3, backoff_seconds=0.01, sleeper=sleep):
    """Open, execute, commit, and close a fresh connection on each attempt.

    `operation(connection)` must perform ALL reads and writes needed to decide
    and apply one transaction. No side effects outside the database.
    """
    if not callable(connect) or not callable(operation) or not callable(sleeper):
        raise TypeError('connect, operation and sleeper must be callable')
    if not isinstance(max_attempts, int) or isinstance(max_attempts, bool) or max_attempts < 1:
        raise ValueError('max_attempts must be a positive integer')
    if isinstance(backoff_seconds, bool) or not isinstance(backoff_seconds, (int, float)) or not isfinite(backoff_seconds) or not 0 <= backoff_seconds <= 5:
        raise ValueError('invalid backoff_seconds')
    for attempt in range(1, max_attempts + 1):
        with closing(connect()) as connection:
            try:
                result = operation(connection)
                connection.commit()
                return result
            except Exception as error:
                try:
                    connection.rollback()
                except Exception:
                    pass
                if not should_retry_transaction(error, attempt, max_attempts):
                    raise
        sleeper(backoff_seconds * attempt)

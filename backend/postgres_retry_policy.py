"""Pure PostgreSQL transaction retry classification; no database side effects.

Caller must rollback and replay the *entire* transaction in a fresh context.
Never retry only the failed SQL statement or retry after external side effects.
"""

RETRYABLE_TRANSACTION_CODES = frozenset({'40001', '40P01'})


def sqlstate_from_error(error):
    """Read structured SQLSTATE from common PostgreSQL drivers and wrappers."""
    visited = set()
    current = error
    while current is not None and id(current) not in visited:
        visited.add(id(current))
        code = getattr(current, 'sqlstate', None) or getattr(current, 'pgcode', None)
        if isinstance(code, str) and len(code) == 5:
            return code
        current = getattr(current, '__cause__', None) or getattr(current, 'orig', None)
    return None


def should_retry_transaction(error, attempt, max_attempts=3):
    """True only for retryable PostgreSQL conflicts with attempts remaining.

    `attempt` is one-based; no retry on the last allowed attempt.
    """
    if not isinstance(attempt, int) or isinstance(attempt, bool) or attempt < 1:
        raise ValueError('attempt must be a positive integer')
    if not isinstance(max_attempts, int) or isinstance(max_attempts, bool) or max_attempts < 1:
        raise ValueError('max_attempts must be a positive integer')
    return attempt < max_attempts and sqlstate_from_error(error) in RETRYABLE_TRANSACTION_CODES

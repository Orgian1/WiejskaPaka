"""Regression: PostgreSQL transaction abort must not mask root cause."""
import pytest
from backend.neon_identity import authenticated_actor


class CleanupFailureConnection:
    def __init__(self):
        self.calls = 0

    def execute(self, query, params=()):
        self.calls += 1
        if self.calls == 2:
            raise RuntimeError('transaction is aborted')


def test_preserve_original_error_when_cleanup_fails():
    connection = CleanupFailureConnection()
    with pytest.raises(ValueError, match='original SQL failure'):
        with authenticated_actor(connection, 17):
            raise ValueError('original SQL failure')
    assert connection.calls == 2


def test_cleanup_failure_is_not_silenced_on_success():
    with pytest.raises(RuntimeError, match='transaction is aborted'):
        with authenticated_actor(CleanupFailureConnection(), 17):
            pass

"""Unit checks for a future whole-transaction PostgreSQL retry boundary."""
from backend.postgres_retry_policy import sqlstate_from_error, should_retry_transaction
import pytest

class Error(Exception):
    def __init__(self, sqlstate=None, pgcode=None, orig=None):
        super().__init__('driver failure')
        self.sqlstate, self.pgcode, self.orig = sqlstate, pgcode, orig

@pytest.mark.parametrize('code', ['40001', '40P01'])
def test_retryable_conflicts_have_bounded_attempts(code):
    err = Error(sqlstate=code)
    assert should_retry_transaction(err, 1)
    assert should_retry_transaction(err, 2)
    assert not should_retry_transaction(err, 3)

@pytest.mark.parametrize('code', ['23505', '23P01', '08006', '57014', None])
def test_other_errors_are_not_automatically_retried(code):
    assert not should_retry_transaction(Error(sqlstate=code), 1)

def test_driver_pgcode_and_wrapped_exception():
    assert sqlstate_from_error(Error(orig=Error(pgcode='40001'))) == '40001'
    assert should_retry_transaction(Error(orig=Error(pgcode='40001')), 1)

def test_cause_chain():
    outer = RuntimeError('wrapper')
    outer.__cause__ = Error(sqlstate='40P01')
    assert should_retry_transaction(outer, 1)

@pytest.mark.parametrize('attempt,limit', [(0,3),(-1,3),(1,0),(True,3),(1,False)])
def test_invalid_retry_bounds_are_rejected(attempt, limit):
    with pytest.raises(ValueError):
        should_retry_transaction(Error(sqlstate='40001'), attempt, limit)

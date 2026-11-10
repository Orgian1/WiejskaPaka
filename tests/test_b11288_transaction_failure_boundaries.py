"""B/11288: transaction retry boundaries before PostgreSQL staging."""
import pytest
from backend.postgres_transaction_runner import run_transaction
from backend.postgres_retry_policy import sqlstate_from_error

class Conn:
    def __init__(self, commit_error=None, rollback_error=None):
        self.commit_error, self.rollback_error = commit_error, rollback_error
        self.commits = self.rollbacks = self.closes = 0
    def commit(self):
        self.commits += 1
        if self.commit_error: raise self.commit_error
    def rollback(self):
        self.rollbacks += 1
        if self.rollback_error: raise self.rollback_error
    def close(self): self.closes += 1

def err(code):
    e = RuntimeError('postgres error')
    e.sqlstate = code
    return e

def test_connection_failure_does_not_retry_or_execute_operation():
    attempts = []
    def connect():
        attempts.append(1)
        raise err('40001')
    with pytest.raises(RuntimeError):
        run_transaction(connect, lambda _: pytest.fail('operation should not run'), sleeper=lambda _: None)
    assert len(attempts) == 1

def test_ambiguous_commit_is_never_replayed():
    conns = []
    def connect():
        c = Conn(commit_error=err('40003')); conns.append(c); return c
    operations = []
    with pytest.raises(RuntimeError):
        run_transaction(connect, lambda _: operations.append('write'), sleeper=lambda _: None)
    assert operations == ['write'] and len(conns) == 1
    assert conns[0].closes == 1

def test_rollback_failure_preserves_original_exception():
    c = Conn(rollback_error=RuntimeError('rollback failed'))
    original = err('23505')
    with pytest.raises(RuntimeError) as captured:
        run_transaction(lambda: c, lambda _: (_ for _ in ()).throw(original), sleeper=lambda _: None)
    assert captured.value is original
    assert c.rollbacks == c.closes == 1

def test_retry_sleep_failure_closes_connection_and_stops():
    c = Conn()
    with pytest.raises(TimeoutError):
        run_transaction(lambda: c, lambda _: (_ for _ in ()).throw(err('40001')),
                        sleeper=lambda _: (_ for _ in ()).throw(TimeoutError('sleep interrupted')))
    assert c.rollbacks == c.closes == 1

def test_nested_driver_error_is_recognized():
    outer = RuntimeError('wrapped')
    outer.__cause__ = err('40P01')
    assert sqlstate_from_error(outer) == '40P01'

def test_success_commits_exactly_once_and_never_sleeps():
    c = Conn()
    result = run_transaction(lambda: c, lambda _: {'status': 'ok'},
                             sleeper=lambda _: pytest.fail('no backoff on success'))
    assert result == {'status': 'ok'}
    assert (c.commits, c.rollbacks, c.closes) == (1, 0, 1)

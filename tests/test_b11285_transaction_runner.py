from types import SimpleNamespace
import pytest
from backend.postgres_transaction_runner import run_transaction

class FakeConnection:
    def __init__(self, *, commit_error=None):
        self.commit_error = commit_error
        self.commits = self.rollbacks = self.closes = 0
    def commit(self):
        self.commits += 1
        if self.commit_error: raise self.commit_error
    def rollback(self): self.rollbacks += 1
    def close(self): self.closes += 1

def pg_error(code):
    err = RuntimeError('database conflict')
    err.sqlstate = code
    return err

def test_retries_entire_operation_and_uses_fresh_connection():
    conns = []
    attempts = []
    def connect():
        con = FakeConnection(); conns.append(con); return con
    def operation(con):
        attempts.append(con)
        if len(attempts) == 1: raise pg_error('40001')
        return 123
    assert run_transaction(connect, operation, sleeper=lambda _: None) == 123
    assert len(conns) == 2 and attempts == conns
    assert conns[0].rollbacks == 1 and conns[0].commits == 0
    assert conns[1].commits == 1
    assert all(c.closes == 1 for c in conns)

def test_commit_conflict_retries_fresh_transaction():
    conns = [FakeConnection(commit_error=pg_error('40P01')), FakeConnection()]
    created = iter(conns)
    assert run_transaction(lambda: next(created), lambda con: 'ok', sleeper=lambda _: None) == 'ok'
    assert conns[0].rollbacks == 1
    assert conns[1].commits == 1
    assert all(c.closes == 1 for c in conns)

@pytest.mark.parametrize('code', ['23505', '42501', '57014'])
def test_non_retryable_error_is_not_replayed(code):
    conns = []
    def connect():
        c = FakeConnection(); conns.append(c); return c
    with pytest.raises(RuntimeError):
        run_transaction(connect, lambda con: (_ for _ in ()).throw(pg_error(code)), sleeper=lambda _: None)
    assert len(conns) == 1 and conns[0].rollbacks == conns[0].closes == 1

def test_bounded_retries():
    conns = []
    def connect():
        c = FakeConnection(); conns.append(c); return c
    with pytest.raises(RuntimeError):
        run_transaction(connect, lambda con: (_ for _ in ()).throw(pg_error('40001')), max_attempts=3, sleeper=lambda _: None)
    assert len(conns) == 3 and all(c.rollbacks == c.closes == 1 for c in conns)

@pytest.mark.parametrize('value', [0, -1, True, 1.5])
def test_invalid_attempt_limit(value):
    with pytest.raises(ValueError): run_transaction(lambda: None, lambda _: None, max_attempts=value)

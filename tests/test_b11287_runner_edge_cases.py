"""Guardrails for retry runner, including ambiguous commits and rollback failures."""
import math
import pytest
from backend.postgres_transaction_runner import run_transaction

class Connection:
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

def error(code):
    exc = RuntimeError('pg failure')
    exc.sqlstate = code
    return exc

@pytest.mark.parametrize('code', ['40003', '08006', '08003', '23505'])
def test_ambiguous_commit_or_nonretryable_error_never_replays(code):
    created = []
    def connect():
        conn = Connection(commit_error=error(code)); created.append(conn); return conn
    with pytest.raises(RuntimeError):
        run_transaction(connect, lambda conn: 'result', sleeper=lambda _: None)
    assert len(created) == 1
    assert (created[0].commits, created[0].rollbacks, created[0].closes) == (1, 1, 1)

def test_rollback_failure_does_not_mask_original_error():
    created = []
    def connect():
        conn = Connection(rollback_error=ValueError('rollback broken')); created.append(conn); return conn
    original = error('42501')
    with pytest.raises(RuntimeError) as captured:
        run_transaction(connect, lambda _: (_ for _ in ()).throw(original), sleeper=lambda _: None)
    assert captured.value is original
    assert created[0].closes == 1

@pytest.mark.parametrize('backoff', [float('nan'), float('inf'), -float('inf'), -0.1, 5.01, True])
def test_invalid_backoff_rejected_without_connecting(backoff):
    with pytest.raises(ValueError):
        run_transaction(lambda: (_ for _ in ()).throw(AssertionError('connected')), lambda _: None, backoff_seconds=backoff)

@pytest.mark.parametrize('field', ['connect', 'operation', 'sleeper'])
def test_callbacks_must_be_callable(field):
    args = dict(connect=lambda: Connection(), operation=lambda _: None, sleeper=lambda _: None)
    args[field] = None
    with pytest.raises(TypeError): run_transaction(**args)

def test_retry_sleep_only_between_attempts():
    connections, delays = [], []
    def connect():
        c = Connection(); connections.append(c); return c
    def operation(_):
        if len(connections) < 3: raise error('40001')
        return 'success'
    assert run_transaction(connect, operation, backoff_seconds=0.2, sleeper=delays.append) == 'success'
    assert delays == pytest.approx([0.2, 0.4])
    assert len(connections) == 3
    assert all(c.closes == 1 for c in connections)

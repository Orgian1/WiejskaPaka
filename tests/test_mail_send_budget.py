from contextlib import closing
from concurrent.futures import ThreadPoolExecutor
import sqlite3
import pytest
from backend.mail_send_budget import Gate,Policy,SCHEMA_SQLITE,load_policy,quarantine_restored
from backend.reset_mail_queue import transaction


@pytest.fixture
def connect(tmp_path):
    path=tmp_path/'budget.sqlite3'
    def factory():
        con=sqlite3.connect(path,timeout=10);con.row_factory=sqlite3.Row;return con
    with closing(factory()) as con:con.executescript(SCHEMA_SQLITE)
    return factory


def claim(connect,gate,now):
    with closing(connect()) as con,transaction(con):return gate.claim(con,now)


def finish(connect,gate):
    with closing(connect()) as con,transaction(con):gate.finish(con)


def test_parallel_claims_only_one_sender_and_finish_spacing(connect):
    gates=[Gate(Policy(1,10),clock=lambda:100.2) for _ in range(8)]
    with ThreadPoolExecutor(max_workers=8) as pool:
        results=list(pool.map(lambda g:claim(connect,g,100),gates))
    assert sum(results)==1
    active=gates[results.index(True)]
    assert not claim(connect,Gate(Policy(1,10)),101)
    finish(connect,active)
    # Ceiling the SMTP completion time prevents fractional-second bursts.
    assert not claim(connect,Gate(Policy(1,10)),101)
    assert claim(connect,Gate(Policy(1,10)),102)


def test_rolling_day_does_not_reset_entire_budget_at_window_boundary(connect):
    policy=Policy(1,2)
    first=Gate(policy,clock=lambda:100);assert claim(connect,first,100);finish(connect,first)
    second=Gate(policy,clock=lambda:86499);assert claim(connect,second,86499);finish(connect,second)
    third=Gate(policy,clock=lambda:86500);assert claim(connect,third,86500);finish(connect,third)
    assert not claim(connect,Gate(policy),86501)
    with closing(connect()) as con:assert con.execute('SELECT count(*) FROM mail_send_attempts').fetchone()[0]==2


def test_crash_keeps_quota_and_stale_finish_cannot_release_new_owner(connect):
    policy=Policy(2,10);first=Gate(policy,clock=lambda:225)
    assert claim(connect,first,100)
    assert not claim(connect,Gate(policy),221)
    next_gate=Gate(policy,clock=lambda:230)
    assert claim(connect,next_gate,222)
    finish(connect,first)
    assert not claim(connect,Gate(policy),225)
    with closing(connect()) as con:
        row=con.execute('SELECT owner FROM mail_send_budget').fetchone()
        assert row['owner']==next_gate.owner
        assert con.execute('SELECT count(*) FROM mail_send_attempts').fetchone()[0]==2


def test_transaction_rollback_restores_capacity_and_policy_mismatch_fails_closed(connect):
    gate=Gate(Policy(1,10))
    with closing(connect()) as con:
        con.execute('BEGIN IMMEDIATE');assert gate.claim(con,100);con.rollback()
    assert claim(connect,gate,100)
    with pytest.raises(ValueError,match='POLICY_MISMATCH'):
        claim(connect,Gate(Policy(1,20)),500)


def test_restore_pauses_even_empty_budget_and_rejects_clock_rollback(connect):
    with closing(connect()) as con,transaction(con):quarantine_restored(con)
    assert not claim(connect,Gate(Policy(1,1)),100)
    with closing(connect()) as con,transaction(con):con.execute('DELETE FROM mail_send_budget')
    gate=Gate(Policy(1,10),clock=lambda:100)
    assert claim(connect,gate,100);finish(connect,gate)
    assert not claim(connect,Gate(Policy(1,10)),99)


@pytest.mark.parametrize('env',[{}, {'WP_MAIL_MIN_INTERVAL_SECONDS':'0','WP_MAIL_DAILY_LIMIT':'1'},
    {'WP_MAIL_MIN_INTERVAL_SECONDS':'1','WP_MAIL_DAILY_LIMIT':'1000001'},
    {'WP_MAIL_MIN_INTERVAL_SECONDS':'1.0','WP_MAIL_DAILY_LIMIT':'10'}])
def test_explicit_validated_policy_required(env):
    with pytest.raises(ValueError,match='POLICY_REJECTED'):load_policy(env)


def test_missing_transaction_rejected(connect):
    with closing(connect()) as con:
        with pytest.raises(ValueError,match='TRANSACTION_REQUIRED'):Gate(Policy(1,1)).claim(con,100)

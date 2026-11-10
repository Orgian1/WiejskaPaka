import sqlite3
import pytest
from backend import email_ownership as proof


@pytest.fixture
def con():
    db=sqlite3.connect(':memory:')
    db.row_factory=sqlite3.Row
    db.execute('CREATE TABLE users(id INTEGER PRIMARY KEY,email TEXT)')
    db.executemany('INSERT INTO users VALUES(?,?)',[(1,'buyer@example.com'),(2,'other@example.com')])
    db.executescript(proof.SCHEMA_SQLITE)
    db.execute('BEGIN IMMEDIATE')
    yield db
    db.close()


def test_proof_single_use_and_hash_only(con):
    token=proof.issue(con,1,now=100)
    assert len(token)==43
    assert token not in str(tuple(con.execute('SELECT * FROM account_email_proofs').fetchone()))
    assert not proof.verified_recipient(con,1,'buyer@example.com')
    assert proof.consume(con,1,token,now=101)
    assert proof.verified_recipient(con,1,'buyer@example.com')
    assert not proof.consume(con,1,token,now=102)
    assert con.execute('SELECT token_hash FROM account_email_proofs').fetchone()[0] is None
    assert proof.issue(con,1,now=1000) is None


@pytest.mark.parametrize('now',[99,1000,1001])
def test_invalid_time_window(con,now):
    token=proof.issue(con,1,now=100)
    assert not proof.consume(con,1,token,now=now)


def test_wrong_account_token_and_recipient(con):
    token=proof.issue(con,1,now=100)
    assert not proof.consume(con,2,token,now=101)
    assert not proof.consume(con,1,'x'*43,now=101)
    assert proof.consume(con,1,token,now=101)
    assert not proof.verified_recipient(con,1,'other@example.com')
    assert not proof.verified_recipient(con,2,'buyer@example.com')


def test_reissue_cooldown_and_invalidation(con):
    first=proof.issue(con,1,now=100)
    assert proof.issue(con,1,now=159) is None
    second=proof.issue(con,1,now=160)
    assert first!=second
    assert not proof.consume(con,1,first,now=161)
    assert proof.consume(con,1,second,now=161)


def test_address_change_invalidates_unconsumed_token(con):
    token=proof.issue(con,1,now=100)
    con.execute('UPDATE users SET email=? WHERE id=1',('new@example.com',))
    assert not proof.consume(con,1,token,now=101)
    fresh=proof.issue(con,1,now=160)
    assert proof.consume(con,1,fresh,now=161)
    assert proof.verified_recipient(con,1,'new@example.com')
    assert not proof.verified_recipient(con,1,'buyer@example.com')


def test_address_change_invalidates_existing_proof(con):
    token=proof.issue(con,1,now=100)
    assert proof.consume(con,1,token,now=101)
    con.execute('UPDATE users SET email=? WHERE id=1',('new@example.com',))
    assert not proof.verified_recipient(con,1,'new@example.com')
    assert not proof.verified_recipient(con,1,'buyer@example.com')


def test_rollback_does_not_verify(con):
    token=proof.issue(con,1,now=100)
    con.commit()
    con.execute('BEGIN IMMEDIATE')
    assert proof.consume(con,1,token,now=101)
    con.rollback()
    assert not proof.verified_recipient(con,1,'buyer@example.com')


def test_transaction_required(con):
    con.commit()
    with pytest.raises(ValueError,match='TRANSACTION_REQUIRED'):
        proof.issue(con,1,now=100)

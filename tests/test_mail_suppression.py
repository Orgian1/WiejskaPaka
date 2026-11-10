from contextlib import closing
import sqlite3
import pytest
from backend import mail_suppression as blocks
from backend.reset_mail_queue import transaction


@pytest.fixture
def con():
    db=sqlite3.connect(':memory:');db.row_factory=sqlite3.Row;db.executescript(blocks.SCHEMA_SQLITE)
    db.execute('BEGIN IMMEDIATE')
    yield db
    db.close()


def test_private_idempotent_block_and_complaint_priority(con):
    blocks.block(con,'Buyer@Example.invalid','permanent_bounce',now=100)
    assert blocks.blocked(con,'buyer@example.invalid')
    assert not blocks.blocked(con,'other@example.invalid')
    blocks.block(con,'buyer@example.invalid','complaint',now=101)
    blocks.block(con,'buyer@example.invalid','permanent_bounce',now=102)
    row=con.execute('SELECT * FROM mail_recipient_blocks').fetchone()
    assert row['reason']=='complaint' and row['created_at']==100
    assert con.execute('SELECT count(*) FROM mail_recipient_blocks').fetchone()[0]==1
    assert 'buyer' not in str(tuple(row)) and '@' not in str(tuple(row))


@pytest.mark.parametrize('reason',['Transient','Delivery','client_says_verified',None])
def test_unknown_or_transient_reason_not_accepted(con,reason):
    with pytest.raises(ValueError,match='SUPPRESSION_REJECTED'):
        blocks.block(con,'buyer@example.invalid',reason,now=100)
    assert not blocks.blocked(con,'buyer@example.invalid')


def test_block_rolls_back_and_requires_transaction(con):
    blocks.block(con,'buyer@example.invalid','complaint',now=100)
    con.rollback();assert not blocks.blocked(con,'buyer@example.invalid')
    with pytest.raises(ValueError,match='TRANSACTION_REQUIRED'):
        blocks.block(con,'buyer@example.invalid','complaint',now=100)

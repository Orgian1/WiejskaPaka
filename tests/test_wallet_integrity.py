"""Reconcile persisted journal arithmetic without disclosing account data."""
import json
import sqlite3
import pytest
from backend.wallet_preview import SCHEMA_SQLITE,AmountIn,move
from backend.wallet_integrity import account_valid,inspect_wallets


@pytest.fixture
def ledger():
    con=sqlite3.connect(':memory:');con.row_factory=sqlite3.Row
    con.execute('CREATE TABLE users(id INTEGER PRIMARY KEY)');con.execute('INSERT INTO users VALUES(1)')
    con.executescript(SCHEMA_SQLITE)
    yield con
    con.close()


def deposit(con,amount,key):
    return move(con,{'id':1},AmountIn(amount_grosze=amount,request_key=key),'topup',now=1793000000)


def test_empty_and_multiple_same_second_entries_reconcile(ledger):
    assert inspect_wallets(ledger)['wallets_checked']==0
    assert deposit(ledger,1234,'first-credit-001')[0]==201
    assert deposit(ledger,999,'second-credit-002')[0]==201
    report=inspect_wallets(ledger)
    assert report=={'success':True,'wallets_checked':1,'entries_checked':2,'inconsistent_wallets':0,'issue_codes':[]}
    assert account_valid(ledger,1)
    assert deposit(ledger,1234,'first-credit-001')[0]==200
    assert inspect_wallets(ledger)==report
    assert 'pin_hash' not in json.dumps(report) and 'user_id' not in report


@pytest.mark.parametrize('damage',[
    'UPDATE wallet_preview_accounts SET available_grosze=available_grosze+1',
    'UPDATE wallet_preview_accounts SET reserved_grosze=1',
    'UPDATE wallet_preview_accounts SET revision=revision+1',
    'UPDATE wallet_preview_entries SET amount_grosze=amount_grosze+1 WHERE revision=1',
    'UPDATE wallet_preview_entries SET available_after=available_after+1 WHERE revision=2',
    'DELETE FROM wallet_preview_entries WHERE revision=1',
])
def test_corruption_is_detected_and_further_credit_is_blocked(ledger,damage):
    deposit(ledger,5000,'credit-one-00001');deposit(ledger,1000,'credit-two-00002')
    ledger.execute(damage)
    before=tuple(ledger.execute('SELECT available_grosze,reserved_grosze,revision FROM wallet_preview_accounts').fetchone())
    report=inspect_wallets(ledger)
    assert not report['success'] and report['inconsistent_wallets']==1 and report['issue_codes']
    assert not account_valid(ledger,1)
    assert deposit(ledger,100,'must-not-credit-003')[0]==409
    assert tuple(ledger.execute('SELECT available_grosze,reserved_grosze,revision FROM wallet_preview_accounts').fetchone())==before


def test_audit_is_read_only_and_bound_is_explicit(ledger):
    deposit(ledger,100,'read-only-credit-1')
    statements=[];ledger.set_trace_callback(statements.append)
    assert inspect_wallets(ledger)['success']
    assert statements and all(sql.lstrip().startswith('SELECT ') for sql in statements)
    with pytest.raises(ValueError):inspect_wallets(ledger,maximum=0)
    ledger.set_trace_callback(None)
    ledger.execute('INSERT INTO users VALUES(2)');ledger.execute('INSERT INTO wallet_preview_accounts(user_id) VALUES(2)')
    with pytest.raises(ValueError,match='capacity'):inspect_wallets(ledger,maximum=1)


def test_cli_default_never_opens_database_and_errors_are_redacted():
    from scripts.check_wallet_integrity import check
    assert check({'WP_TEST_DATABASE_URL':'private-password'})=={'status':'DISABLED'}
    result=check({'WP_TEST_DATABASE_URL':'private-password'},enabled=True)
    assert result=={'status':'WALLET_CHECK_REJECTED','success':False}
    assert 'private-password' not in json.dumps(result)

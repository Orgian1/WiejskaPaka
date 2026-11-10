"""Real localhost wallet cancellation/finalization; no bank or PSP transport."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
import sqlite3
from uuid import uuid4
import pytest
from backend.wallet_integrity import inspect_wallets
from tests.test_wallet_preview_http import account,deposit,set_pin,withdraw,PASSWORD
from tests.test_admin_seller_review import create_admin
from tests.test_purchase_record_http_restart import server


@pytest.fixture
def wallet_db(tmp_path,monkeypatch):
    monkeypatch.setenv('WP_ENABLE_WALLET_PREVIEW','1')
    return tmp_path/'wallet.sqlite3'


def admin(client,database):
    def promote(uid):
        with sqlite3.connect(database) as con:con.execute("UPDATE users SET role='admin' WHERE id=?",(uid,))
    return create_admin(client,promote)[0]


def queue(client,headers):return client.get('/admin/wallet/withdrawals-test',headers=headers)
def cancel(client,headers,oid):return client.post(f'/wallet/withdrawals/{oid}/cancel-test',headers=headers)
def complete(client,headers,oid):return client.post(f'/admin/wallet/withdrawals/{oid}/complete-test',headers=headers)


def setup(client,role='rolnik'):
    owner=account(client,role);deposit(client,owner);set_pin(client,owner)
    response=withdraw(client,owner,amount=4001);assert response.status_code==201
    return owner,response.json()['id']


def audit(database):
    with closing(sqlite3.connect(database)) as con:
        con.row_factory=sqlite3.Row
        result=inspect_wallets(con)
        assert result['success'],result
        return result


@pytest.mark.parametrize('action',['cancel','complete'])
def test_resolution_is_idempotent_and_durable(wallet_db,action):
    with server(wallet_db) as client:
        owner,oid=setup(client);operator=admin(client,wallet_db)
        expected=withdrawal=client.get('/wallet',headers=owner).json()['entries'][0]['withdrawal_preview']
        assert expected['fee_grosze']==200 and expected['net_grosze']==3801
        assert queue(client,operator).json()['items'][0]['id']==oid
        operation=(lambda:cancel(client,owner,oid)) if action=='cancel' else (lambda:complete(client,operator,oid))
        first=operation();assert first.status_code==201 and first.json()['transfer_executed'] is False
        retry=operation();assert retry.status_code==200 and retry.json()==first.json()
        opposite=complete(client,operator,oid) if action=='cancel' else cancel(client,owner,oid)
        assert opposite.status_code==409
        assert queue(client,operator).json()['items']==[]
    with server(wallet_db) as client:
        state=client.get('/wallet',headers=owner).json()
        assert (state['available_grosze'],state['reserved_grosze'])==((10000,0) if action=='cancel' else (5999,0))
        assert state['entries'][0]['state']==('cancelled_test' if action=='cancel' else 'completed_test')
        assert state['entries'][0]['withdrawal_preview']==withdrawal
        assert audit(wallet_db)['entries_checked']==3
        # Further credits/debits must still reconcile across the terminal event.
        assert deposit(client,owner,amount=100).status_code==201
        assert withdraw(client,owner,amount=100).status_code==201
        assert audit(wallet_db)['entries_checked']==5


def test_account_roles_permissions_and_private_queue(wallet_db):
    with server(wallet_db) as client:
        owner,oid=setup(client);other=account(client);courier=account(client,'dostawca');operator=admin(client,wallet_db)
        assert queue(client,{}).status_code==401
        for actor in (owner,other,courier):
            assert queue(client,actor).status_code==403
            assert complete(client,actor,oid).status_code==403
        assert cancel(client,other,oid).status_code==404
        assert cancel(client,courier,oid).status_code==403
        assert cancel(client,operator,oid).status_code==403
        assert client.get('/admin/wallet/withdrawals-test?limit=101',headers=operator).status_code==422
        assert client.get('/admin/wallet/withdrawals-test?offset=-1',headers=operator).status_code==422
        text=queue(client,operator).text
        assert 'password' not in text and 'pin_hash' not in text and 'email' not in text
        assert complete(client,operator,'missing').status_code==404
        audit(wallet_db)


def test_parallel_cancel_and_complete_have_only_one_winner(wallet_db):
    with server(wallet_db) as client:
        owner,oid=setup(client);operator=admin(client,wallet_db)
        with ThreadPoolExecutor(max_workers=2) as pool:
            results=list(pool.map(lambda action:cancel(client,owner,oid) if action=='cancel' else complete(client,operator,oid),['cancel','complete']))
        assert sorted(r.status_code for r in results)==[201,409]
        state=client.get('/wallet',headers=owner).json()
        assert state['reserved_grosze']==0 and state['available_grosze'] in (5999,10000)
        audit(wallet_db)


def test_duplicate_completion_and_parallel_new_withdrawal(wallet_db):
    with server(wallet_db) as client:
        owner,oid=setup(client);operator=admin(client,wallet_db)
        with ThreadPoolExecutor(max_workers=2) as pool:
            codes=list(pool.map(lambda _:complete(client,operator,oid).status_code,range(2)))
        assert sorted(codes)==[200,201]
        with ThreadPoolExecutor(max_workers=2) as pool:
            codes=list(pool.map(lambda _:withdraw(client,owner,amount=5000).status_code,range(2)))
        assert sorted(codes)==[201,409]
        audit(wallet_db)


def test_resolution_failure_rolls_back_balance_and_journal(wallet_db):
    with server(wallet_db) as client:
        owner,oid=setup(client)
        with sqlite3.connect(wallet_db) as con:
            con.execute("CREATE TRIGGER break_resolution BEFORE INSERT ON wallet_preview_resolutions BEGIN SELECT RAISE(ABORT,'synthetic'); END")
        assert cancel(client,owner,oid).status_code==500
    with server(wallet_db) as client:
        state=client.get('/wallet',headers=owner).json()
        assert (state['available_grosze'],state['reserved_grosze'])==(5999,4001)
        assert state['entries'][0]['state']=='pending'
        audit(wallet_db)


def test_terms_are_frozen_and_database_updates_are_rejected(wallet_db):
    with server(wallet_db) as client:
        owner,oid=setup(client,role='klient');key=uuid4().hex
        first=withdraw(client,owner,amount=1,key=key)
        uid=client.get('/auth/me',headers=owner).json()['id']
        with sqlite3.connect(wallet_db) as con:
            con.execute("UPDATE users SET role='rolnik' WHERE id=?",(uid,))
            with pytest.raises(sqlite3.IntegrityError):con.execute('UPDATE wallet_preview_terms SET fee_basis_points=500 WHERE withdrawal_id=?',(oid,))
        state=client.get('/wallet',headers=owner).json()
        assert state['withdrawal_fee_basis_points']==500
        frozen=next(x for x in state['entries'] if x['id']==oid)['withdrawal_preview']
        assert frozen['fee_basis_points']==0 and frozen['net_grosze']==4001
        assert withdraw(client,owner,amount=1,key=key).json()==first.json()
        assert cancel(client,owner,oid).status_code==201
        audit(wallet_db)


def test_replay_after_terminal_state_returns_current_state(wallet_db):
    with server(wallet_db) as client:
        owner=account(client);deposit(client,owner);set_pin(client,owner)
        key=uuid4().hex;oid=withdraw(client,owner,key=key).json()['id']
        assert cancel(client,owner,oid).status_code==201
        reply=withdraw(client,owner,key=key)
        assert reply.status_code==200 and reply.json()['state']=='cancelled_test'
        assert client.get('/wallet',headers=owner).json()['available_grosze']==10000
        audit(wallet_db)


def test_upgrade_preserves_legacy_pending_withdrawals(wallet_db):
    with server(wallet_db) as client:
        owner,oid=setup(client)
        before=client.get('/wallet',headers=owner).json()
    with sqlite3.connect(wallet_db) as con:
        con.execute('DROP TABLE wallet_preview_resolutions')
        con.execute('DROP TABLE wallet_preview_terms')
    with server(wallet_db) as client:
        assert client.get('/wallet',headers=owner).json()==before
        assert cancel(client,owner,oid).status_code==201
        assert client.get('/wallet',headers=owner).json()['available_grosze']==10000
        audit(wallet_db)


def test_resolution_events_and_terms_cannot_be_mutated(wallet_db):
    with server(wallet_db) as client:
        owner,oid=setup(client);cancel(client,owner,oid)
    with sqlite3.connect(wallet_db) as con:
        for sql in ("UPDATE wallet_preview_resolutions SET state='completed_test'",'DELETE FROM wallet_preview_resolutions','DELETE FROM wallet_preview_terms'):
            with pytest.raises(sqlite3.IntegrityError):con.execute(sql)
    audit(wallet_db)


def test_audit_works_with_database_enforced_read_only_mode(wallet_db):
    with server(wallet_db) as client:
        owner,oid=setup(client);cancel(client,owner,oid)
    with closing(sqlite3.connect(wallet_db)) as con:
        con.row_factory=sqlite3.Row
        con.execute('PRAGMA query_only=ON')
        assert inspect_wallets(con)['success']

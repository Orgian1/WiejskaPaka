"""Real HTTP recovery, durable negative receipts and late-write exclusion."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
import sqlite3
from uuid import uuid4
import pytest
from tests.test_wallet_preview_http import account,deposit,set_pin,withdraw
from tests.test_wallet_withdrawal_lifecycle import wallet_db,admin,audit,cancel
from tests.test_purchase_record_http_restart import server


def recover(client,owner,key,kind='topup',amount=100):
    return client.post('/wallet/operations/reconcile-test',headers=owner,
        json={'request_key':key,'kind':kind,'amount_grosze':amount})


@pytest.mark.parametrize('kind',['topup','withdrawal'])
def test_absent_operation_is_fenced_before_any_late_request(wallet_db,kind):
    with server(wallet_db) as client:
        owner=account(client);deposit(client,owner);set_pin(client,owner)
        before=client.get('/wallet',headers=owner).json();key=uuid4().hex
        response=recover(client,owner,key,kind)
        assert response.status_code==200 and response.json()=={'outcome':'released','transfer_executed':False}
        assert recover(client,owner,key,kind).json()==response.json()
    with server(wallet_db) as client:
        late=deposit(client,owner,amount=100,key=key) if kind=='topup' else withdraw(client,owner,amount=100,key=key)
        assert late.status_code==409
        assert client.get('/wallet',headers=owner).json()==before
        # Changing a fenced payload or switching operation type cannot resurrect it.
        assert deposit(client,owner,amount=999,key=key).status_code==409
        assert withdraw(client,owner,amount=999,key=key).status_code==409
        assert deposit(client,owner,amount=100).status_code==201
        audit(wallet_db)


@pytest.mark.parametrize('kind',['topup','withdrawal'])
def test_known_operation_is_reported_without_a_second_mutation(wallet_db,kind):
    with server(wallet_db) as client:
        owner=account(client);deposit(client,owner);set_pin(client,owner);key=uuid4().hex
        first=deposit(client,owner,amount=500,key=key) if kind=='topup' else withdraw(client,owner,amount=500,key=key)
        before=client.get('/wallet',headers=owner).json()
        # Local storage may contain a stale amount/kind: report the actual server entry.
        result=recover(client,owner,key,'withdrawal' if kind=='topup' else 'topup',999).json()
        assert result=={'outcome':'committed','id':first.json()['id'],'kind':kind,'amount_grosze':500,'state':first.json()['state'],'transfer_executed':False}
        assert client.get('/wallet',headers=owner).json()==before
        with closing(sqlite3.connect(wallet_db)) as con:
            assert con.execute('SELECT count(*) FROM wallet_preview_operation_fences').fetchone()[0]==0
        if kind=='withdrawal':
            assert cancel(client,owner,first.json()['id']).status_code==201
            assert recover(client,owner,key).json()['state']=='cancelled_test'
        audit(wallet_db)


@pytest.mark.parametrize('kind',['topup','withdrawal'])
def test_parallel_recovery_and_original_request_cannot_both_release_and_commit(wallet_db,kind):
    with server(wallet_db) as client:
        owner=account(client);deposit(client,owner);set_pin(client,owner)
        for _ in range(4):
            key=uuid4().hex
            def original():return deposit(client,owner,amount=100,key=key) if kind=='topup' else withdraw(client,owner,amount=100,key=key)
            with ThreadPoolExecutor(max_workers=2) as pool:
                write=pool.submit(original);resolution=pool.submit(recover,client,owner,key,kind)
                a,b=write.result(),resolution.result()
            assert b.status_code==200
            assert (a.status_code,b.json()['outcome']) in ((201,'committed'),(409,'released'))
            retry=recover(client,owner,key,kind)
            assert retry.json()==b.json()
            audit(wallet_db)


def test_scope_validation_and_immutable_fences(wallet_db):
    with server(wallet_db) as client:
        owner=account(client);other=account(client);courier=account(client,'dostawca');operator=admin(client,wallet_db)
        key=uuid4().hex;deposit(client,owner,key=key)
        assert recover(client,{},key).status_code==401
        for actor in (courier,operator):assert recover(client,actor,key).status_code==403
        assert recover(client,other,key).json()['outcome']=='released'
        assert recover(client,owner,key).json()['outcome']=='committed'
        for bad in ({'amount_grosze':True},{'amount_grosze':1.5},{'kind':'withdraw'},{'user_id':1},{'pin':'123456'},{'request_key':'bad'}):
            body={'request_key':uuid4().hex,'kind':'topup','amount_grosze':100,**bad}
            assert client.post('/wallet/operations/reconcile-test',headers=owner,json=body).status_code==422
    with sqlite3.connect(wallet_db) as con:
        for sql in ('DELETE FROM wallet_preview_operation_fences','UPDATE wallet_preview_operation_fences SET amount_grosze=101'):
            with pytest.raises(sqlite3.IntegrityError):con.execute(sql)
    audit(wallet_db)


def test_fenced_request_does_not_spend_pin_attempts(wallet_db):
    with server(wallet_db) as client:
        owner=account(client);deposit(client,owner);set_pin(client,owner);key=uuid4().hex
        assert recover(client,owner,key,'withdrawal').json()['outcome']=='released'
        for _ in range(6):assert withdraw(client,owner,amount=100,key=key,pin='000000').status_code==409
        assert withdraw(client,owner,amount=100).status_code==201
        audit(wallet_db)


def test_fence_insert_failure_leaves_balances_and_key_unmodified(wallet_db):
    with server(wallet_db) as client:
        owner=account(client);deposit(client,owner);key=uuid4().hex
        with sqlite3.connect(wallet_db) as con:
            con.execute("CREATE TRIGGER break_fence BEFORE INSERT ON wallet_preview_operation_fences BEGIN SELECT RAISE(ABORT,'synthetic'); END")
        assert recover(client,owner,key).status_code==500
    with sqlite3.connect(wallet_db) as con:
        assert con.execute('SELECT count(*) FROM wallet_preview_operation_fences').fetchone()[0]==0
        con.execute('DROP TRIGGER break_fence')
    with server(wallet_db) as client:
        assert deposit(client,owner,amount=100,key=key).status_code==201
        audit(wallet_db)


def test_audit_detects_entry_added_with_an_already_fenced_key(wallet_db):
    with server(wallet_db) as client:
        owner=account(client);key=uuid4().hex;deposit(client,owner,key=key)
    with sqlite3.connect(wallet_db) as con:
        uid=con.execute('SELECT user_id FROM wallet_preview_accounts').fetchone()[0]
        con.execute('INSERT INTO wallet_preview_operation_fences VALUES(?,?,?,?,?)',(uid,key,'topup',100,1794000000))
    from backend.wallet_integrity import inspect_wallets
    with closing(sqlite3.connect(wallet_db)) as con:
        con.row_factory=sqlite3.Row
        result=inspect_wallets(con)
        assert not result['success'] and 'OPERATION_FENCE_MISMATCH' in result['issue_codes']
    with server(wallet_db) as client:
        assert deposit(client,owner,amount=1).status_code==409

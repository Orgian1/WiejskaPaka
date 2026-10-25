"""Persistent private wallet preview over real HTTP; never bank transfers."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
import sqlite3
from uuid import uuid4
import pytest
from tests.test_purchase_record_http_restart import server

PASSWORD='SyntheticWalletPassword2026!'


def account(client,role='klient'):
    body={'email':uuid4().hex+'@example.invalid','password':PASSWORD,'role':role}
    assert client.post('/auth/register',json=body).status_code==201
    return {'Authorization':'Bearer '+client.post('/auth/login',json=body).json()['access_token']}


def deposit(client,headers,amount=10000,key=None):
    return client.post('/wallet/topups',headers=headers,json={'amount_grosze':amount,'request_key':key or uuid4().hex})


def set_pin(client,headers,pin='123456',password=PASSWORD):
    return client.put('/wallet/pin',headers=headers,json={'pin':pin,'password':password})


def withdraw(client,headers,amount=4000,pin='123456',key=None):
    return client.post('/wallet/withdrawals',headers=headers,json={'amount_grosze':amount,'pin':pin,'request_key':key or uuid4().hex})


@pytest.fixture
def enabled(tmp_path,monkeypatch):
    monkeypatch.setenv('WP_ENABLE_WALLET_PREVIEW','1')
    return tmp_path/'wallet.sqlite3'


def test_wallet_persists_and_retries_never_duplicate_credit_or_reservation(enabled):
    with server(enabled) as client:
        buyer=account(client);other=account(client)
        assert client.get('/wallet').status_code==401
        assert client.get('/wallet',headers=buyer).json()['available_grosze']==0
        key=uuid4().hex
        first=deposit(client,buyer,key=key);assert first.status_code==201
        assert deposit(client,buyer,key=key).status_code==200
        assert deposit(client,buyer,amount=20000,key=key).status_code==409
        assert client.get('/wallet',headers=other).json()['available_grosze']==0
        assert withdraw(client,buyer).status_code==409
        assert set_pin(client,buyer).status_code==200
        assert withdraw(client,buyer,pin='000000').status_code==403
        key=uuid4().hex
        assert withdraw(client,buyer,key=key).status_code==201
        assert withdraw(client,buyer,key=key).status_code==200
        assert withdraw(client,buyer,key=key,pin='000000').status_code==403
        state=client.get('/wallet',headers=buyer).json()
        assert (state['available_grosze'],state['reserved_grosze'])==(6000,4000)
        assert len(state['entries'])==2 and state['entries'][0]['kind']=='withdrawal'
        assert 'pin_hash' not in state and 'password' not in str(state)
    with server(enabled) as client:
        state=client.get('/wallet',headers=buyer).json()
        assert (state['available_grosze'],state['reserved_grosze'])==(6000,4000)
        assert state['pin_configured'] and len(state['entries'])==2
        assert withdraw(client,buyer,amount=7000).status_code==409
    with closing(sqlite3.connect(enabled)) as con:
        encoded=con.execute('SELECT pin_hash FROM wallet_preview_accounts WHERE pin_hash IS NOT NULL').fetchone()[0]
        assert encoded.startswith('$argon2') and encoded!='123456'


def test_bad_pin_lockout_survives_restart_and_topup_needs_no_pin(enabled):
    with server(enabled) as client:
        buyer=account(client);assert set_pin(client,buyer).status_code==200
        assert deposit(client,buyer).status_code==201
        for _ in range(5):assert withdraw(client,buyer,pin='000000').status_code==403
        assert withdraw(client,buyer).status_code==429
        assert set_pin(client,buyer,pin='654321').status_code==429
    with server(enabled) as client:
        assert withdraw(client,buyer).status_code==429
        assert deposit(client,buyer,amount=100).status_code==201
        state=client.get('/wallet',headers=buyer).json()
        assert state['available_grosze']==10100 and state['reserved_grosze']==0


def test_password_required_to_set_or_change_pin_and_role_is_enforced(enabled):
    with server(enabled) as client:
        buyer=account(client);courier=account(client,'dostawca')
        assert set_pin(client,buyer,password='wrong').status_code==403
        assert set_pin(client,buyer).status_code==200
        assert set_pin(client,buyer,pin='654321',password='wrong').status_code==403
        assert deposit(client,courier).status_code==403
        assert client.get('/wallet',headers=courier).status_code==403
        assert client.post('/wallet/topups',headers=buyer,json={'amount_grosze':100,'request_key':uuid4().hex,'user_id':99}).status_code==422
        for amount in (-1,0,1.5,True,100000001):
            assert deposit(client,buyer,amount=amount).status_code==422


def test_parallel_withdrawals_cannot_spend_the_same_balance_twice(enabled):
    with server(enabled) as client:
        buyer=account(client);set_pin(client,buyer);deposit(client,buyer)
        with ThreadPoolExecutor(max_workers=2) as pool:
            codes=list(pool.map(lambda _:withdraw(client,buyer,amount=7000).status_code,range(2)))
        assert sorted(codes)==[201,409]
        state=client.get('/wallet',headers=buyer).json()
        assert (state['available_grosze'],state['reserved_grosze'])==(3000,7000)
        key=uuid4().hex
        with ThreadPoolExecutor(max_workers=2) as pool:
            assert sorted(pool.map(lambda _:deposit(client,buyer,amount=100,key=key).status_code,range(2)))==[200,201]
        assert client.get('/wallet',headers=buyer).json()['available_grosze']==3100


def test_journal_failure_rolls_back_credit(enabled):
    with server(enabled) as client:
        buyer=account(client)
        with closing(sqlite3.connect(enabled)) as con:
            con.execute("CREATE TRIGGER fail_wallet BEFORE INSERT ON wallet_preview_entries BEGIN SELECT RAISE(ABORT,'synthetic'); END");con.commit()
        assert deposit(client,buyer).status_code==500
        with closing(sqlite3.connect(enabled)) as con:
            assert con.execute('SELECT coalesce(sum(available_grosze),0) FROM wallet_preview_accounts').fetchone()[0]==0
            assert con.execute('SELECT count(*) FROM wallet_preview_entries').fetchone()[0]==0


def test_disabled_wallet_and_production_optin_are_rejected(tmp_path):
    from backend.wallet_preview import validate_environment
    with pytest.raises(ValueError):validate_environment({'WP_ENABLE_WALLET_PREVIEW':'1','WP_ENV':'production'})
    with server(tmp_path/'off.sqlite3') as client:
        buyer=account(client)
        assert client.get('/wallet',headers=buyer).status_code==404

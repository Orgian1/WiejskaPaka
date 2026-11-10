from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4
import pytest
from tests.test_purchase_record_http_restart import server,setup,checkout,account
OLD='Disposable-private-record-123!'
NEW='New-disposable-HTTP-password!'


@pytest.mark.parametrize('cart',[False,True])
def test_password_change_revokes_all_devices_but_preserves_purchase_and_pin_after_restart(tmp_path,cart):
    db=tmp_path/'password.sqlite3'
    with server(db) as client:
        farmer,buyer,products=setup(client);_,ids,original=checkout(client,buyer,products,cart)
        me=client.get('/auth/me',headers=buyer).json();email=me['email']
        second=client.post('/auth/login',json={'email':email,'password':OLD}).json()['access_token']
        other_device={'Authorization':'Bearer '+second};url=f'/orders/{ids[0]}/recover-pin-test'
        before=client.get(f'/orders/{ids[0]}/purchase-record',headers=buyer).json()
        assert client.post(url,headers=buyer,json={'password':OLD}).status_code==200
        key_file=tmp_path/'password.sqlite3.checkout-key';key_before=key_file.read_bytes()
        changed=client.post('/auth/change-password',headers=buyer,json={'current_password':OLD,'new_password':NEW})
        assert changed.status_code==200,changed.text
        assert changed.headers['cache-control']=='no-store' and key_file.read_bytes()==key_before
        for old in (buyer,other_device):
            assert client.get('/auth/me',headers=old).status_code==401
            assert client.post(url,headers=old,json={'password':OLD}).status_code==401
        assert client.get('/auth/me',headers=farmer).status_code==200
    with server(db) as client:
        assert client.get('/auth/me',headers=buyer).status_code==401
        assert client.post('/auth/login',json={'email':email,'password':OLD}).status_code==401
        login=client.post('/auth/login',json={'email':email,'password':NEW});assert login.status_code==200
        current={'Authorization':'Bearer '+login.json()['access_token']}
        recovered=client.post(url,headers=current,json={'password':NEW});assert recovered.status_code==200,recovered.text
        assert recovered.json()['pin_test_only']==original['shipment_pin_test_only' if cart else 'pin_test_only']
        assert client.get(f'/orders/{ids[0]}/purchase-record',headers=current).json()==before
        assert {o['id'] for o in client.get('/orders/me',headers=current).json()}==set(ids)
    import sqlite3
    with sqlite3.connect(db) as con:
        assert con.execute('SELECT attempts FROM checkout_pin_access WHERE buyer_id=?',(me['id'],)).fetchone()[0]==2


def test_racing_old_password_logins_cannot_survive_a_completed_change(tmp_path):
    with server(tmp_path/'race.sqlite3') as client:
        for _ in range(5):
            headers=account(client,'klient');email=client.get('/auth/me',headers=headers).json()['email']
            def run(kind):
                if kind=='change':return client.post('/auth/change-password',headers=headers,json={'current_password':OLD,'new_password':NEW})
                return client.post('/auth/login',json={'email':email,'password':OLD})
            with ThreadPoolExecutor(max_workers=2) as pool:changed,login=list(pool.map(run,['change','login']))
            assert changed.status_code==200,changed.text
            assert login.status_code in (200,401)
            if login.status_code==200:
                assert client.get('/auth/me',headers={'Authorization':'Bearer '+login.json()['access_token']}).status_code==401
            assert client.get('/auth/me',headers=headers).status_code==401
            assert client.post('/auth/login',json={'email':email,'password':NEW}).status_code==200


def test_password_change_attempt_budget_survives_server_restart(tmp_path):
    db=tmp_path/'password-budget.sqlite3'
    with server(db) as client:
        headers=account(client,'klient')
        for _ in range(3):
            r=client.post('/auth/change-password',headers=headers,json={'current_password':'wrong','new_password':NEW})
            assert r.status_code==401
    with server(db) as client:
        for _ in range(2):
            r=client.post('/auth/change-password',headers=headers,json={'current_password':'wrong','new_password':NEW})
            assert r.status_code==401
        r=client.post('/auth/change-password',headers=headers,json={'current_password':OLD,'new_password':NEW})
        assert r.status_code==429 and 1<=int(r.headers['retry-after'])<=900
        assert client.get('/auth/me',headers=headers).status_code==200

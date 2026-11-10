"""Real TCP HTTP and restart persistence for account-scoped revocation."""
from concurrent.futures import ThreadPoolExecutor
import pytest
from tests.test_purchase_record_http_restart import server,setup,checkout,account
from tests.test_account_security_http import OLD


@pytest.mark.parametrize('cart',[False,True])
def test_sessions_survive_restart_and_revocation_preserves_purchase_pin_and_key(tmp_path,cart):
    db=tmp_path/'sessions.sqlite3'
    with server(db) as c:
        farmer,buyer,products=setup(c);_,ids,original=checkout(c,buyer,products,cart)
        email=c.get('/auth/me',headers=buyer).json()['email']
        login=c.post('/auth/login',json={'email':email,'password':OLD});assert login.status_code==200
        second={'Authorization':'Bearer '+login.json()['access_token']}
        record=c.get(f'/orders/{ids[0]}/purchase-record',headers=buyer).json()
        key=(tmp_path/'sessions.sqlite3.checkout-key').read_bytes()
        assert c.get('/auth/sessions',headers=buyer).json()['active_sessions']==2
    with server(db) as c:
        assert c.get('/auth/sessions',headers=buyer).json()['active_sessions']==2
        r=c.post('/auth/logout-others',headers=buyer);assert r.status_code==200 and r.headers['cache-control']=='no-store'
        assert c.get('/auth/me',headers=second).status_code==401
        assert c.get('/auth/me',headers=farmer).status_code==200
        assert c.get(f'/orders/{ids[0]}/purchase-record',headers=buyer).json()==record
        pin=c.post(f'/orders/{ids[0]}/recover-pin-test',headers=buyer,json={'password':OLD})
        assert pin.status_code==200 and pin.json()['pin_test_only']==original['shipment_pin_test_only' if cart else 'pin_test_only']
        assert (tmp_path/'sessions.sqlite3.checkout-key').read_bytes()==key
    with server(db) as c:
        assert c.get('/auth/me',headers=second).status_code==401
        assert c.get('/auth/sessions',headers=buyer).json()['active_sessions']==1
        assert c.post('/auth/logout-all',headers=buyer).status_code==200
    with server(db) as c:
        assert c.get('/auth/me',headers=buyer).status_code==401
        fresh=c.post('/auth/login',json={'email':email,'password':OLD});assert fresh.status_code==200
        h={'Authorization':'Bearer '+fresh.json()['access_token']}
        assert c.get(f'/orders/{ids[0]}/purchase-record',headers=h).json()==record


def test_concurrent_devices_revocation_over_real_http(tmp_path):
    with server(tmp_path/'sessions-race.sqlite3') as c:
        for _ in range(6):
            h=account(c,'klient');email=c.get('/auth/me',headers=h).json()['email']
            second=c.post('/auth/login',json={'email':email,'password':OLD}).json()['access_token']
            extra={'Authorization':'Bearer '+second}
            with ThreadPoolExecutor(max_workers=2) as pool:responses=list(pool.map(lambda auth:c.post('/auth/logout-others',headers=auth),[h,extra]))
            assert sorted(r.status_code for r in responses)==[200,401]
            assert sorted(c.get('/auth/me',headers=x).status_code for x in [h,extra])==[200,401]

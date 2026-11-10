from datetime import datetime,timedelta,timezone
import json
from uuid import uuid4
import pytest
from fastapi import Header
from fastapi.testclient import TestClient
from backend import app as api
from tests.test_purchase_records import purchase
from tests.test_b10921_security_boundaries import actor


@pytest.mark.parametrize('cart',[False,True])
def test_replay_secret_is_sealed_at_rest_and_survives_retention(cart):
    c,f,b,pids,point,pbody,result,ids,url,body,headers=purchase(cart=cart)
    buyer=api.current_user(b['Authorization'])['id'];key=headers['Idempotency-Key'];key=key if cart else 'direct:'+key
    with api.db() as con:
        row=con.execute('SELECT * FROM checkout_idempotency WHERE buyer_id=? AND request_key=?',(buyer,key)).fetchone()
        envelope=json.loads(row['response_json']);field='shipment_pin_test_only' if cart else 'pin_test_only'
        assert field not in row['response_json'] and envelope['format']=='wp-checkout-aesgcm-v1'
    assert c.post(url,headers=headers,json=body).json()==result
    future=datetime.fromisoformat(envelope['pin_until'])+timedelta(seconds=1)
    assert api.run_checkout_retention(now=future)>=1
    after=c.post(url,headers=headers,json=body)
    assert after.status_code==201 and after.json()['pin_available'] is False and field not in after.json()
    assert (after.json().get('shipment_id') if cart else after.json()['id'])==(result.get('shipment_id') if cart else result['id'])
    with api.db() as con:
        row=con.execute('SELECT * FROM checkout_idempotency WHERE buyer_id=? AND request_key=?',(buyer,key)).fetchone()
        assert field not in api.CHECKOUT_VAULT._decrypt(row['response_json'],buyer,key,row['payload_hash'])[0]


@pytest.mark.parametrize('cart',[False,True])
def test_tampered_replay_returns_409_without_creating_another_order(cart):
    c,f,b,pids,point,pbody,result,ids,url,body,headers=purchase(cart=cart)
    buyer=api.current_user(b['Authorization'])['id'];key=headers['Idempotency-Key'];key=key if cart else 'direct:'+key
    with api.db() as con:
        count=con.execute('SELECT COUNT(*) FROM orders').fetchone()[0]
        row=con.execute('SELECT response_json FROM checkout_idempotency WHERE buyer_id=? AND request_key=?',(buyer,key)).fetchone()
        data=json.loads(row['response_json']);data['pin_until']='2099-01-01T00:00:00+00:00'
        con.execute('UPDATE checkout_idempotency SET response_json=? WHERE buyer_id=? AND request_key=?',(json.dumps(data),buyer,key))
    r=c.post(url,headers=headers,json=body)
    assert r.status_code==409 and 'pin_test_only' not in r.text
    with api.db() as con:assert con.execute('SELECT COUNT(*) FROM orders').fetchone()[0]==count


@pytest.mark.parametrize('endpoint',['direct','cart','status'])
@pytest.mark.parametrize('change',['logout','expire','role'])
def test_replay_checks_live_session_in_its_transaction(endpoint,change):
    c,f,b,pids,point,pbody,result,ids,url,body,headers=purchase(cart=endpoint=='cart')
    def stale_dependency(authorization: str | None=Header(default=None)):
        user=api.current_user(authorization)
        with api.db() as con:
            if change=='role':con.execute('UPDATE users SET role=? WHERE id=?',('dostawca',user['id']))
            elif change=='logout':con.execute('DELETE FROM sessions WHERE token_hash=?',(api.token_hash(authorization.split()[1]),))
            else:con.execute('UPDATE sessions SET expires_at=? WHERE token_hash=?',('2000-01-01T00:00:00+00:00',api.token_hash(authorization.split()[1])))
        return user
    api.app.dependency_overrides[api.current_user]=stale_dependency
    try:
        r=c.get('/orders/idempotency-status/'+headers['Idempotency-Key'],headers=b) if endpoint=='status' else c.post(url,headers=headers,json=body)
    finally:api.app.dependency_overrides.pop(api.current_user,None)
    assert r.status_code==(403 if change=='role' else 401),r.text
    assert 'pin_test_only' not in r.text


@pytest.mark.parametrize('cart',[False,True])
def test_encryption_failure_rolls_back_checkout_and_same_key_can_be_retried(monkeypatch,cart):
    c,f,b,pids,point,pbody,result,ids,url,body,headers=purchase(cart=cart)
    if cart:
        for pid in pids:assert c.put('/cart/items',headers=b,json={'product_id':pid,'quantity':1}).status_code==200
    headers={**b,'Idempotency-Key':uuid4().hex}
    with api.db() as con:
        before={table:con.execute('SELECT COUNT(*) FROM '+table).fetchone()[0] for table in
                ('orders','shipment_groups','order_purchase_records','inventory_reservations','checkout_idempotency')}
        stock={pid:con.execute('SELECT stock FROM products WHERE id=?',(pid,)).fetchone()[0] for pid in pids}
    def fail(*args,**kwargs):raise RuntimeError('PRIVATE_ENCRYPTION_FAILURE_DETAIL')
    with monkeypatch.context() as patch:
        patch.setattr(api.CHECKOUT_VAULT,'seal',fail)
        response=TestClient(api.app,raise_server_exceptions=False).post(url,headers=headers,json=body)
    assert response.status_code==500 and 'PRIVATE_ENCRYPTION_FAILURE_DETAIL' not in response.text
    with api.db() as con:
        assert all(con.execute('SELECT COUNT(*) FROM '+table).fetchone()[0]==count for table,count in before.items())
        assert all(con.execute('SELECT stock FROM products WHERE id=?',(pid,)).fetchone()[0]==quantity for pid,quantity in stock.items())
    if cart:assert len(c.get('/cart/items',headers=b).json()['items'])==len(pids)
    success=c.post(url,headers=headers,json=body)
    assert success.status_code==201,success.text
    assert c.post(url,headers=headers,json=body).json()==success.json()

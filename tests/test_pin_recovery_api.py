"""Reauthentication, ownership, retention and unchanged fulfillment invariants."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timedelta,timezone
import json
from uuid import uuid4
import pytest
from fastapi import Header
from fastapi.testclient import TestClient
from backend import app as api
from tests.test_purchase_records import purchase
from tests.test_b10921_security_boundaries import actor

PASSWORD='Disposable-PIN-recovery-123!'


def prepared(cart=False,fulfillment='odbior'):
    data=purchase(cart=cart,fulfillment=fulfillment)
    buyer=api.current_user(data[2]['Authorization'])['id']
    with api.db() as con:con.execute('UPDATE users SET password_hash=? WHERE id=?',(api.ph.hash(PASSWORD),buyer))
    return data,buyer


def endpoint(data,shipment=False):
    return f'/shipments/{data[6]["shipment_id"]}/recover-pin-test' if shipment else f'/orders/{data[7][0]}/recover-pin-test'


def recover(data,password=PASSWORD,shipment=False,headers=None):
    return data[0].post(endpoint(data,shipment),headers=data[2] if headers is None else headers,json={'password':password})


@pytest.mark.parametrize('cart,shipment',[(False,False),(True,False),(True,True)])
@pytest.mark.parametrize('fulfillment',['odbior','dostawa'])
def test_recovery_returns_original_pin_without_checkout_or_fulfillment_mutation(cart,shipment,fulfillment):
    data,bid=prepared(cart,fulfillment);c,f,b,pids,point,pbody,result,ids,*_=data
    tables=('orders','products','inventory_reservations','order_purchase_records','checkout_idempotency','shipment_groups','shipment_order_links')
    with api.db() as con:before={t:[tuple(r) for r in con.execute('SELECT * FROM '+t).fetchall()] for t in tables}
    r=recover(data,shipment=shipment)
    assert r.status_code==200,r.text
    expected=result['shipment_pin_test_only' if cart else 'pin_test_only']
    assert r.json()=={'mode':'test','pin_test_only':expected,'order_ids':ids,'shipment_id':result.get('shipment_id'),
        'notice':'Sprawdź towar przed przekazaniem PIN-u. Zakup już istnieje; nie składaj go ponownie.'}
    assert r.headers['cache-control']=='no-store' and r.headers['pragma']=='no-cache'
    with api.db() as con:
        assert {t:[tuple(r) for r in con.execute('SELECT * FROM '+t).fetchall()] for t in tables}==before
        assert con.execute('SELECT attempts FROM checkout_pin_access WHERE buyer_id=?',(bid,)).fetchone()[0]==1
    for oid in ids:
        assert expected not in c.get(f'/orders/{oid}/purchase-record',headers=b).text
    if not cart:
        if fulfillment=='odbior':
            assert c.post(f'/test/orders/{ids[0]}/ready',headers=f).status_code==200
            done=c.post(f'/orders/{ids[0]}/confirm',headers=f,json={'pin':expected,'checked_goods':True})
            assert done.status_code==200 and done.json()['confirmed']
            assert recover(data).status_code==409


@pytest.mark.parametrize('cart,shipment',[(False,False),(True,True)])
@pytest.mark.parametrize('who',['anonymous','stranger','rolnik','dostawca','admin'])
def test_pin_is_not_available_to_any_other_principal(cart,shipment,who):
    data,bid=prepared(cart)
    if who=='anonymous':headers={};expected=401
    else:headers,_=actor('klient' if who=='stranger' else who);expected=404 if who=='stranger' else 403
    r=recover(data,shipment=shipment,headers=headers)
    assert r.status_code==expected,r.text
    assert 'pin_test_only' not in r.text
    with api.db() as con:assert con.execute('SELECT attempts FROM checkout_pin_access WHERE buyer_id=?',(bid,)).fetchone() is None


@pytest.mark.parametrize('change',['logout','expire','role'])
def test_recovery_rechecks_session_inside_transaction(change):
    data,bid=prepared()
    def stale(authorization: str | None=Header(default=None)):
        user=api.current_user(authorization)
        with api.db() as con:
            if change=='role':con.execute('UPDATE users SET role=? WHERE id=?',('dostawca',bid))
            elif change=='logout':con.execute('DELETE FROM sessions WHERE user_id=?',(bid,))
            else:con.execute('UPDATE sessions SET expires_at=? WHERE user_id=?',('2000-01-01T00:00:00+00:00',bid))
        return user
    api.app.dependency_overrides[api.current_user]=stale
    try:r=recover(data)
    finally:api.app.dependency_overrides.pop(api.current_user,None)
    assert r.status_code==(403 if change=='role' else 401)
    assert 'pin_test_only' not in r.text


def test_rate_limit_commits_failures_across_tokens_orders_and_successes_then_resets():
    data,bid=prepared(True)
    for _ in range(4):assert recover(data,'WRONG-PASSWORD').status_code==401
    assert recover(data).status_code==200
    with api.db() as con:
        new_token=uuid4().hex
        con.execute('INSERT INTO sessions(token_hash,user_id,expires_at) VALUES(?,?,?)',
            (api.token_hash(new_token),bid,(datetime.now(timezone.utc)+timedelta(hours=1)).isoformat()))
    r=recover(data,shipment=True,headers={'Authorization':'Bearer '+new_token})
    assert r.status_code==429 and 1<=int(r.headers['retry-after'])<=900
    with api.db() as con:
        con.execute('UPDATE checkout_pin_access SET window_started_at=? WHERE buyer_id=?',
            ((datetime.now(timezone.utc)-timedelta(minutes=16)).isoformat(),bid))
    assert recover(data,shipment=True).status_code==200
    with api.db() as con:assert con.execute('SELECT attempts FROM checkout_pin_access WHERE buyer_id=?',(bid,)).fetchone()[0]==1


def test_concurrent_valid_requests_share_a_single_account_budget():
    data,bid=prepared()
    with ThreadPoolExecutor(max_workers=8) as pool:codes=list(pool.map(lambda _:recover(data).status_code,range(8)))
    assert codes.count(200)==5 and codes.count(429)==3,codes
    with api.db() as con:assert con.execute('SELECT attempts FROM checkout_pin_access WHERE buyer_id=?',(bid,)).fetchone()[0]==5


@pytest.mark.parametrize('change',['cancelled','used','blocked','unpaid_expired','retention_expired','redacted','corrupt','wrong_hash','missing_link','refunded'])
def test_unavailable_pin_never_resets_or_replaces_purchase(change):
    data,bid=prepared();oid=data[7][0]
    with api.db() as con:
        if change=='cancelled':con.execute("UPDATE orders SET status='anulowane_testowo' WHERE id=?",(oid,))
        elif change=='used':con.execute('UPDATE orders SET pin_used=1 WHERE id=?',(oid,))
        elif change=='blocked':con.execute('UPDATE orders SET pin_attempts=5 WHERE id=?',(oid,))
        elif change=='wrong_hash':con.execute('UPDATE orders SET pin_hash=? WHERE id=?',(api.ph.hash('not-the-PIN'),oid))
        elif change=='missing_link':con.execute('DELETE FROM checkout_pin_links WHERE order_id=?',(oid,))
        elif change=='unpaid_expired':con.execute('UPDATE inventory_reservations SET expires_at=? WHERE order_id=?',('2000-01-01T00:00:00+00:00',oid))
        elif change=='refunded':
            # Use the supported payment writer, not a fabricated financial row.
            pass
        else:
            row=con.execute('SELECT * FROM checkout_idempotency WHERE buyer_id=?',(bid,)).fetchone()
            raw=json.loads(row['response_json'])
            if change=='corrupt':raw['pin_until']='2099-01-01T00:00:00+00:00';stored=json.dumps(raw)
            else:
                decoded=api.CHECKOUT_VAULT.open(row['response_json'],bid,row['request_key'],row['payload_hash'])
                if change=='redacted':decoded.pop('pin_test_only')
                stored=api.CHECKOUT_VAULT.seal(decoded,bid,row['request_key'],row['payload_hash'],
                    pin_until='2000-01-01T00:00:00+00:00' if change=='retention_expired' else raw['pin_until'])
            con.execute('UPDATE checkout_idempotency SET response_json=? WHERE buyer_id=?',(stored,bid))
    if change=='refunded':
        import os
        previous=os.environ.get('WP_ENABLE_TEST_PAYMENTS');os.environ['WP_ENABLE_TEST_PAYMENTS']='1'
        try:
            r=data[0].post(f'/test/payments/{oid}/events',headers=data[2],json={'event_id':uuid4().hex,'event_type':'payment_success_test'})
            assert r.status_code==200,r.text
            r=data[0].post(f'/orders/{oid}/cancel-paid-test',headers=data[2])
            assert r.status_code==200,r.text
        finally:
            if previous is None:os.environ.pop('WP_ENABLE_TEST_PAYMENTS',None)
            else:os.environ['WP_ENABLE_TEST_PAYMENTS']=previous
    with api.db() as con:before=tuple(con.execute('SELECT * FROM orders WHERE id=?',(oid,)).fetchone())
    r=recover(data);assert r.status_code==409,r.text
    assert 'pin_test_only' not in r.text and 'ponownie' in r.text
    with api.db() as con:
        assert tuple(con.execute('SELECT * FROM orders WHERE id=?',(oid,)).fetchone())==before
        assert con.execute('SELECT attempts FROM checkout_pin_access WHERE buyer_id=?',(bid,)).fetchone()[0]==1
        if change=='corrupt':
            con.execute('UPDATE checkout_idempotency SET response_json=? WHERE buyer_id=?',(row['response_json'],bid))


@pytest.mark.parametrize('body',[{}, {'password':''},{'password':'x'*257},{'password':123},{'password':PASSWORD,'pin':'000000'},{'password':PASSWORD,'buyer_id':1}])
def test_strict_bounded_request_never_echoes_password(body):
    data,_=prepared();r=data[0].post(endpoint(data),headers=data[2],json=body)
    assert r.status_code==422
    assert PASSWORD not in r.text and 'x'*257 not in r.text


def test_corrupt_or_missing_password_hash_cannot_recover():
    data,bid=prepared()
    with api.db() as con:con.execute('UPDATE users SET password_hash=? WHERE id=?',('invalid',bid))
    assert recover(data).status_code==401


@pytest.mark.parametrize('cart',[False,True])
def test_paid_purchase_can_recover_after_inventory_hold_deadline(monkeypatch,cart):
    data,bid=prepared(cart);monkeypatch.setenv('WP_ENABLE_TEST_PAYMENTS','1')
    for oid in data[7]:
        r=data[0].post(f'/test/payments/{oid}/events',headers=data[2],json={'event_id':uuid4().hex,'event_type':'payment_success_test'})
        assert r.status_code==200,r.text
    with api.db() as con:
        for oid in data[7]:con.execute('UPDATE inventory_reservations SET expires_at=? WHERE order_id=?',('2000-01-01T00:00:00+00:00',oid))
    assert recover(data,shipment=cart).status_code==200


@pytest.mark.parametrize('cart',[False,True])
def test_one_blocked_shipment_position_blocks_whole_recovery(cart):
    data,bid=prepared(True)
    with api.db() as con:con.execute('UPDATE orders SET pin_attempts=5 WHERE id=?',(data[7][-1],))
    assert recover(data,shipment=cart).status_code==409
    with api.db() as con:assert con.execute('SELECT pin_attempts FROM orders WHERE id=?',(data[7][-1],)).fetchone()[0]==5


def test_substituted_mapping_cannot_disclose_a_different_pin():
    data,bid=prepared();c=data[0];headers={**data[2],'Idempotency-Key':uuid4().hex}
    second=c.post(data[8],headers=headers,json=data[9]);assert second.status_code==201
    with api.db() as con:
        con.execute('UPDATE checkout_pin_links SET request_key=? WHERE order_id=?',('direct:'+headers['Idempotency-Key'],data[7][0]))
    assert recover(data).status_code==409
    with api.db() as con:
        con.execute('UPDATE checkout_pin_links SET request_key=? WHERE order_id=?',('direct:'+data[10]['Idempotency-Key'],data[7][0]))


def test_backfill_uses_authenticated_ids_and_does_not_extend_retention():
    from backend.pin_recovery import backfill_links
    data,bid=prepared(True)
    with api.db() as con:
        con.execute('DELETE FROM checkout_pin_links WHERE buyer_id=?',(bid,))
        before=con.execute('SELECT response_json FROM checkout_idempotency WHERE buyer_id=?',(bid,)).fetchone()[0]
        backfill_links(con,api.CHECKOUT_VAULT)
        assert con.execute('SELECT response_json FROM checkout_idempotency WHERE buyer_id=?',(bid,)).fetchone()[0]==before
        assert con.execute('SELECT COUNT(*) FROM checkout_pin_links WHERE buyer_id=?',(bid,)).fetchone()[0]==len(data[7])
    assert recover(data,shipment=True).status_code==200


def test_backfill_rejects_cross_buyer_order_and_rolls_back_links():
    from backend.pin_recovery import backfill_links
    from backend.checkout_vault import CheckoutStorageError
    data,bid=prepared();other,otherid=actor('klient')
    with api.db() as con:
        con.execute('DELETE FROM checkout_pin_links WHERE buyer_id=?',(bid,))
        sealed=api.CHECKOUT_VAULT.seal({'id':data[7][0]},otherid,'test-backfill-invalid','hash',pin_until=(datetime.now(timezone.utc)+timedelta(hours=1)).isoformat())
        con.execute('INSERT INTO checkout_idempotency VALUES(?,?,?,?,?)',(otherid,'test-backfill-invalid','hash',sealed,datetime.now(timezone.utc).isoformat()))
    with pytest.raises(CheckoutStorageError):
        with api.db() as con:backfill_links(con,api.CHECKOUT_VAULT)
    with api.db() as con:assert con.execute('SELECT order_id FROM checkout_pin_links WHERE buyer_id=?',(bid,)).fetchone() is None


def test_success_does_not_reset_bad_pin_attempts_or_hold_deadline():
    data,bid=prepared();oid=data[7][0]
    with api.db() as con:
        con.execute('UPDATE orders SET pin_attempts=4 WHERE id=?',(oid,))
        hold=tuple(con.execute('SELECT * FROM inventory_reservations WHERE order_id=?',(oid,)).fetchone())
    assert recover(data).status_code==200
    with api.db() as con:
        assert con.execute('SELECT pin_attempts FROM orders WHERE id=?',(oid,)).fetchone()[0]==4
        assert tuple(con.execute('SELECT * FROM inventory_reservations WHERE order_id=?',(oid,)).fetchone())==hold


@pytest.mark.parametrize('cart',[False,True])
def test_link_write_failure_rolls_back_whole_checkout(monkeypatch,cart):
    data,bid=prepared(cart);c=data[0];headers={**data[2],'Idempotency-Key':uuid4().hex}
    if cart:
        for pid in data[3]:assert c.put('/cart/items',headers=data[2],json={'product_id':pid,'quantity':1}).status_code==200
    tables=('orders','products','inventory_reservations','order_purchase_records','checkout_idempotency','checkout_pin_links','shipment_groups','saved_cart_items')
    with api.db() as con:before={t:[tuple(r) for r in con.execute('SELECT * FROM '+t).fetchall()] for t in tables}
    original=api.link_reply
    def fail(*args,**kwargs):original(*args,**kwargs);raise RuntimeError('PRIVATE-LINK-DETAIL')
    with monkeypatch.context() as patch:
        patch.setattr(api,'link_reply',fail)
        r=TestClient(api.app,raise_server_exceptions=False).post(data[8],headers=headers,json=data[9])
    assert r.status_code==500 and 'PRIVATE-LINK-DETAIL' not in r.text
    with api.db() as con:assert {t:[tuple(r) for r in con.execute('SELECT * FROM '+t).fetchall()] for t in tables}==before
    retried=c.post(data[8],headers=headers,json=data[9]);assert retried.status_code==201,retried.text
    assert c.post(data[8],headers=headers,json=data[9]).json()==retried.json()

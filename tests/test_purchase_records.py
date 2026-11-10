"""Historical terms, money, insert-only SQL controls and private read authorization."""
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4
import sqlite3
import pytest
from fastapi.testclient import TestClient
from backend import app as api
from backend.purchase_records import audit_records
from tests.test_b10921_security_boundaries import actor


def purchase(*,cart=False,fulfillment='odbior'):
    c=TestClient(api.app);farmer,fid=actor('rolnik');buyer,bid=actor('klient')
    point_body={'name':'Stary punkt','city':'Opole','street':'Pierwotna 1','opening_hours':'9–17',
        'latitude_e6':52_000_000,'longitude_e6':16_000_000}
    point=c.post('/pickup-points',headers=farmer,json=point_body).json()['id']
    products=[]
    for name,price,fee in [('Pierwotne jabłka',199,501),('Pierwotne ziemniaki',301,399)][:2 if cart else 1]:
        r=c.post('/products',headers=farmer,json={'name':name,'price_grosze':price,'delivery_grosze':fee,'stock':10})
        assert r.status_code==201;products.append(r.json()['id'])
    body={'fulfillment':fulfillment}
    if fulfillment=='odbior':body['pickup_point_id']=point
    else:body.update(delivery_city='Prywatne miasto',delivery_street='Prywatna ulica 99',delivery_postal_code='45-001')
    headers={**buyer,'Idempotency-Key':uuid4().hex}
    if cart:
        for pid in products:assert c.put('/cart/items',headers=buyer,json={'product_id':pid,'quantity':2}).status_code==200
        url='/cart/checkout-test'
    else:
        url='/orders';body.update(product_id=products[0],quantity=2)
    response=c.post(url,headers=headers,json=body);assert response.status_code==201,response.text
    receipt=response.json();ids=[o['id'] for o in receipt['orders']] if cart else [receipt['id']]
    return c,farmer,buyer,products,point,point_body,receipt,ids,url,body,headers


def read(c,buyer,oid):
    r=c.get(f'/orders/{oid}/purchase-record',headers=buyer);assert r.status_code==200,r.text
    return r.json()


@pytest.mark.parametrize('cart',[False,True])
@pytest.mark.parametrize('fulfillment',['odbior','dostawa'])
def test_original_terms_are_atomic_and_integer(cart,fulfillment):
    c,f,b,pids,point,pbody,result,ids,*_=purchase(cart=cart,fulfillment=fulfillment)
    for index,oid in enumerate(ids):
        record=read(c,b,oid);original=record['original']
        assert record['original_available'] and record['mode']=='test'
        assert original['product']['name']==('Pierwotne jabłka' if index==0 else 'Pierwotne ziemniaki')
        assert type(original['product']['unit_price_grosze']) is int
        assert original['product']['unit_price_grosze']*original['quantity']==original['subtotal_grosze']
        assert original['subtotal_grosze']+original['delivery_grosze']==original['total_grosze']
        if fulfillment=='odbior':
            assert original['pickup_point']['street']=='Pierwotna 1'
            assert original['pickup_point']['latitude_e6']==52_000_000
        else:
            assert original['pickup_point'] is None
            assert 'Prywatna' not in str(record) and 'Prywatne miasto' not in str(record)
        assert read(c,f,oid)['original']==original
    if cart:
        r=c.get(f'/shipments/{result["shipment_id"]}/purchase-record',headers=b)
        assert r.status_code==200 and r.json()['original_available']
        assert r.json()['original']['delivery_grosze']==(501 if fulfillment=='dostawa' else 0)
        assert r.json()['original']['total_grosze']==(1501 if fulfillment=='dostawa' else 1000)


@pytest.mark.parametrize('cart',[False,True])
def test_later_product_and_point_edits_do_not_rewrite_purchase(cart):
    c,f,b,pids,point,pbody,result,ids,*_=purchase(cart=cart)
    before=[read(c,b,oid)['original'] for oid in ids]
    for oid in ids:
        # Close without implying payment; original terms must also survive cancellation.
        if not cart:assert c.post(f'/orders/{oid}/cancel-test',headers=b).status_code==200
    if cart:assert c.post(f'/shipments/{result["shipment_id"]}/cancel-test',headers=b).status_code==200
    for pid in pids:
        assert c.patch(f'/products/mine/{pid}',headers=f,json={'name':'Nowa nazwa','price_grosze':9999,'delivery_grosze':9999}).status_code==200
    assert c.put(f'/pickup-points/{point}',headers=f,json={**pbody,'name':'Nowy punkt','street':'Nowy adres 99',
        'opening_hours':'20–21','latitude_e6':51_000_000,'active':True}).status_code==200
    assert [read(c,b,oid)['original'] for oid in ids]==before
    assert all(read(c,b,oid)['current']['status']=='anulowane_testowo' for oid in ids)


@pytest.mark.parametrize('operation',[
    'UPDATE order_purchase_records SET product_name=? WHERE order_id=?',
    'DELETE FROM order_purchase_records WHERE order_id=?',
    'INSERT OR REPLACE INTO order_purchase_records SELECT * FROM order_purchase_records WHERE order_id=?',
])
def test_sql_cannot_update_delete_or_replace_record(operation):
    c,f,b,pids,point,pbody,result,ids,*_=purchase()
    before=read(c,b,ids[0])
    with pytest.raises(sqlite3.IntegrityError):
        with api.db() as con:
            con.execute(operation,('Zmienione',ids[0]) if operation.startswith('UPDATE') else (ids[0],))
    assert read(c,b,ids[0])==before


@pytest.mark.parametrize('cart',[False,True])
def test_same_key_replay_never_inserts_second_record(cart):
    c,f,b,pids,point,pbody,result,ids,url,body,headers=purchase(cart=cart)
    assert c.post(url,headers=headers,json=body).json()==result
    with api.db() as con:
        for oid in ids:assert con.execute('SELECT COUNT(*) AS n FROM order_purchase_records WHERE order_id=?',(oid,)).fetchone()['n']==1


@pytest.mark.parametrize('cart',[False,True])
def test_capture_failure_rolls_back_every_checkout_write(monkeypatch,cart):
    from backend import purchase_records
    c,f,b,pids,point,pbody,result,ids,url,body,headers=purchase(cart=cart)
    if cart:
        for pid in pids:assert c.put('/cart/items',headers=b,json={'product_id':pid,'quantity':1}).status_code==200
    def fail(*args):raise RuntimeError('record failure')
    monkeypatch.setattr(purchase_records,'capture_purchase',fail)
    with api.db() as con:
        old_orders=con.execute('SELECT COUNT(*) AS n FROM orders').fetchone()['n']
        old_shipments=con.execute('SELECT COUNT(*) AS n FROM shipment_groups').fetchone()['n']
        stock={pid:con.execute('SELECT stock FROM products WHERE id=?',(pid,)).fetchone()['stock'] for pid in pids}
    r=TestClient(api.app,raise_server_exceptions=False).post(url,headers={**b,'Idempotency-Key':uuid4().hex},json=body)
    assert r.status_code==500 and 'record failure' not in r.text
    with api.db() as con:
        assert con.execute('SELECT COUNT(*) AS n FROM orders').fetchone()['n']==old_orders
        assert con.execute('SELECT COUNT(*) AS n FROM shipment_groups').fetchone()['n']==old_shipments
        assert all(con.execute('SELECT stock FROM products WHERE id=?',(pid,)).fetchone()['stock']==stock[pid] for pid in pids)
    if cart:assert len(c.get('/cart/items',headers=b).json()['items'])==len(pids)


@pytest.mark.parametrize('cart',[False,True])
def test_private_authorization_and_no_pin_or_delivery_address(cart):
    c,f,b,pids,point,pbody,result,ids,*_=purchase(cart=cart,fulfillment='dostawa')
    stranger,_=actor('klient');other_farmer,_=actor('rolnik');courier,_=actor('dostawca');admin,_=actor('admin')
    url=f'/shipments/{result["shipment_id"]}/purchase-record' if cart else f'/orders/{ids[0]}/purchase-record'
    assert c.get(url).status_code==401
    for who in (stranger,other_farmer):assert c.get(url,headers=who).status_code==404
    for who in (courier,admin):assert c.get(url,headers=who).status_code==403
    for who in (b,f):
        r=c.get(url,headers=who);assert r.status_code==200
        assert r.headers['cache-control']=='no-store'
        assert all(key not in r.text for key in ('pin_test_only','pin_hash','password_hash','token_hash','phone','Prywatna ulica'))


def test_original_record_survives_paid_refund_and_keeps_current_state(monkeypatch):
    monkeypatch.setenv('WP_ENABLE_TEST_PAYMENTS','1')
    c,f,b,pids,point,pbody,result,ids,*_=purchase(fulfillment='dostawa')
    oid=ids[0];before=read(c,b,oid)['original']
    paid=c.post(f'/test/payments/{oid}/events',headers=b,json={'event_id':uuid4().hex,'event_type':'payment_success_test'})
    assert paid.status_code==200
    assert c.post(f'/orders/{oid}/cancel-paid-test',headers=b).json()['refund_grosze']==899
    after=read(c,b,oid)
    assert after['original']==before and after['current']['refund_grosze']==899
    assert after['current']['payment_state_test']=='refunded_test'


def test_order_money_tampering_is_reported_without_disclosing_record():
    c,f,b,pids,point,pbody,result,ids,*_=purchase()
    with api.db() as con:
        con.execute('UPDATE orders SET subtotal_grosze=subtotal_grosze+1,total_grosze=total_grosze+1 WHERE id=?',(ids[0],))
        report=audit_records(con)
    assert not report['consistent'] and any(i['order_id']==ids[0] for i in report['issues'])
    r=c.get(f'/orders/{ids[0]}/purchase-record',headers=b)
    assert r.status_code==409 and 'Pierwotne jabłka' not in r.text


def test_admin_audit_is_private_readonly_and_has_no_addresses():
    c,f,b,pids,point,pbody,result,ids,*_=purchase()
    admin,_=actor('admin');url='/admin/orders/purchase-record-audit'
    assert c.get(url).status_code==401
    for who in (b,f):assert c.get(url,headers=who).status_code==403
    r=c.get(url,headers=admin);assert r.status_code==200 and r.json()['read_only']
    assert all(s not in r.text for s in ('Pierwotna','Opole','Pierwotne jabłka','phone','pin'))


def test_older_order_without_record_is_not_reconstructed_from_todays_catalog():
    c,f,b,pids,point,pbody,result,ids,*_=purchase()
    with api.db() as con:
        old=con.execute('''INSERT INTO orders(buyer_id,farmer_id,product_id,quantity,subtotal_grosze,delivery_grosze,
            total_grosze,fulfillment,status,pickup_code,pin_hash,created_at)
            SELECT buyer_id,farmer_id,product_id,quantity,subtotal_grosze,delivery_grosze,total_grosze,fulfillment,
            status,?,pin_hash,? FROM orders WHERE id=?''',('WP-OLD-'+uuid4().hex,'2020-01-01T00:00:00+00:00',ids[0])).lastrowid
        con.execute('INSERT INTO order_locations(order_id,pickup_point_id) VALUES(?,?)',(old,point))
    r=read(c,b,old)
    assert not r['original_available'] and r['original'] is None
    assert 'Pierwotne jabłka' not in str(r)
    with api.db() as con:
        audit=audit_records(con)
    assert old in audit['orders_without_original_record'] and not audit['complete']


@pytest.mark.parametrize('cart',[False,True])
def test_changing_catalog_prices_before_payment_cannot_change_refund(monkeypatch,cart):
    monkeypatch.setenv('WP_ENABLE_TEST_PAYMENTS','1')
    c,f,b,pids,point,pbody,result,ids,*_=purchase(cart=cart,fulfillment='dostawa')
    before=[read(c,b,oid)['original'] for oid in ids]
    for pid in pids:assert c.patch(f'/products/mine/{pid}',headers=f,json={'price_grosze':9999,'delivery_grosze':9999,'name':'Nowa oferta'}).status_code==200
    for oid in ids:
        paid=c.post(f'/test/payments/{oid}/events',headers=b,json={'event_id':uuid4().hex,'event_type':'payment_success_test'})
        assert paid.status_code==200
    url=f'/shipments/{result["shipment_id"]}/cancel-paid-test' if cart else f'/orders/{ids[0]}/cancel-paid-test'
    assert c.post(url,headers=b).json()['refund_grosze']==(1501 if cart else 899)
    assert [read(c,b,oid)['original'] for oid in ids]==before


def test_completed_pickup_keeps_original_point_even_after_later_move():
    c,f,b,pids,point,pbody,result,ids,*_=purchase()
    oid=ids[0];original=read(c,b,oid)['original']
    assert c.post(f'/test/orders/{oid}/ready',headers=f).status_code==200
    assert c.post(f'/orders/{oid}/confirm',headers=f,json={'pin':result['pin_test_only'],'checked_goods':True}).json()['confirmed']
    assert c.put(f'/pickup-points/{point}',headers=f,json={**pbody,'street':'Późniejszy adres 99','active':True}).status_code==200
    assert read(c,b,oid)['original']==original


def test_concurrent_same_key_checkout_creates_one_purchase_record():
    c,f,b,pids,point,pbody,result,ids,url,body,headers=purchase()
    new_headers={**b,'Idempotency-Key':uuid4().hex}
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(lambda _:TestClient(api.app).post(url,headers=new_headers,json=body),range(2)))
    assert all(r.status_code==201 for r in results)
    assert results[0].json()==results[1].json()
    with api.db() as con:
        assert con.execute('SELECT COUNT(*) AS n FROM order_purchase_records WHERE order_id=?',(results[0].json()['id'],)).fetchone()['n']==1


def test_changed_location_link_is_detected_as_inconsistent():
    c,f,b,pids,point,pbody,result,ids,*_=purchase()
    other=c.post('/pickup-points',headers=f,json={**pbody,'street':'Druga 2'}).json()['id']
    with api.db() as con:
        con.execute('UPDATE order_locations SET pickup_point_id=? WHERE order_id=?',(other,ids[0]))
        report=audit_records(con)
    assert any(i['order_id']==ids[0] and i['code']=='ORDER_RECORD_LOCATION_MISMATCH' for i in report['issues'])
    assert c.get(f'/orders/{ids[0]}/purchase-record',headers=b).status_code==409


def test_reservation_expiry_keeps_the_original_deadline_and_terms():
    from datetime import datetime,timedelta,timezone
    from backend.inventory_reservations import expire_due
    c,f,b,pids,point,pbody,result,ids,*_=purchase()
    original=read(c,b,ids[0])['original']
    with api.db() as con:
        con.execute('UPDATE inventory_reservations SET expires_at=? WHERE order_id=?',
                    ((datetime.now(timezone.utc)-timedelta(seconds=1)).isoformat(),ids[0]))
        expire_due(con,now=datetime.now(timezone.utc),postgres=False,record_event=api.record_order_event)
    after=read(c,b,ids[0])
    assert after['original']==original
    assert after['current']['status']=='anulowane_testowo'


def test_point_without_coordinates_still_has_original_address():
    c,f,b,pids,point,pbody,result,ids,*_=purchase()
    assert c.post(f'/orders/{ids[0]}/cancel-test',headers=b).status_code==200
    assert c.put(f'/pickup-points/{point}',headers=f,json={**{k:v for k,v in pbody.items() if k not in ('latitude_e6','longitude_e6')},'clear_coordinates':True,'active':True}).status_code==200
    r=c.post('/orders',headers=b,json={'product_id':pids[0],'quantity':1,'fulfillment':'odbior','pickup_point_id':point})
    assert r.status_code==201
    original=read(c,b,r.json()['id'])['original']
    assert original['pickup_point']['street']=='Pierwotna 1'
    assert original['pickup_point']['latitude_e6'] is None
    assert original['pickup_point']['longitude_e6'] is None


def test_mixed_legacy_shipment_does_not_guess_original_group_total():
    c,f,b,pids,point,pbody,result,ids,*_=purchase(cart=True)
    # Simulate pre-migration data without disabling immutable-record controls:
    # attach an old cloned order, which never had a record, to the group.
    with api.db() as con:
        old=con.execute('''INSERT INTO orders(buyer_id,farmer_id,product_id,quantity,subtotal_grosze,delivery_grosze,
            total_grosze,fulfillment,status,pickup_code,pin_hash,created_at)
            SELECT buyer_id,farmer_id,product_id,quantity,subtotal_grosze,delivery_grosze,total_grosze,fulfillment,
            status,?,pin_hash,created_at FROM orders WHERE id=?''',('WP-OLD-'+uuid4().hex,ids[0])).lastrowid
        con.execute('INSERT INTO order_locations(order_id,pickup_point_id) VALUES(?,?)',(old,point))
        con.execute('INSERT INTO shipment_order_links(shipment_id,order_id) VALUES(?,?)',(result['shipment_id'],old))
    r=c.get(f'/shipments/{result["shipment_id"]}/purchase-record',headers=b)
    assert r.status_code==200,r.text
    assert r.json()['original_available'] is False and r.json()['original'] is None
    assert sum(o['original_available'] for o in r.json()['orders'])==2


@pytest.mark.parametrize('endpoint',['order','shipment','audit'])
@pytest.mark.parametrize('change',['logout','expire','role'])
def test_record_read_rechecks_auth_inside_its_snapshot(endpoint,change):
    from fastapi import Header
    c,f,b,pids,point,pbody,result,ids,*_=purchase(cart=True)
    headers=actor('admin')[0] if endpoint=='audit' else b
    urls={'order':f'/orders/{ids[0]}/purchase-record',
          'shipment':f'/shipments/{result["shipment_id"]}/purchase-record',
          'audit':'/admin/orders/purchase-record-audit'}
    def stale_dependency(authorization: str | None=Header(default=None)):
        user=api.current_user(authorization)
        token=authorization.split(' ',1)[1]
        with api.db() as con:
            if change=='logout':con.execute('DELETE FROM sessions WHERE token_hash=?',(api.token_hash(token),))
            elif change=='expire':con.execute('UPDATE sessions SET expires_at=? WHERE token_hash=?',('2000-01-01T00:00:00+00:00',api.token_hash(token)))
            else:con.execute('UPDATE users SET role=? WHERE id=?',('dostawca',user['id']))
        return user
    api.app.dependency_overrides[api.current_user]=stale_dependency
    try:r=c.get(urls[endpoint],headers=headers)
    finally:api.app.dependency_overrides.pop(api.current_user,None)
    assert r.status_code==(403 if change=='role' else 401),r.text
    assert 'Pierwotne' not in r.text and 'records_present' not in r.text

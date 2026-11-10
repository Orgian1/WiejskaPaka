from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from uuid import uuid4
import pytest
from backend import app as module
from tests.test_address_delivery_http import actors, create, setup, new_product


def test_pickup_auto_ready_after_payment_and_pin_without_checkbox(actors, monkeypatch):
    client, users = actors
    farmer, _, buyer, _, _ = users
    monkeypatch.setenv('WP_ENABLE_AUTOMATIC_PICKUP','1')
    point=client.post('/pickup-points',headers=farmer[0],json={'name':'Odbiór automatyczny','city':'Legnica','street':'Testowa 22','opening_hours':'7–10'}).json()['id']
    pid=new_product(client,farmer[0])
    order=client.post('/orders',headers=buyer[0],json={'product_id':pid,'quantity':2,'fulfillment':'odbior','pickup_point_id':point}).json()
    event={'event_id':uuid4().hex,'event_type':'payment_success_test'}
    assert client.post(f'/test/payments/{order["id"]}/events',headers=buyer[0],json=event).status_code==200
    stored=next(o for o in client.get('/orders/me',headers=farmer[0]).json() if o['id']==order['id'])
    assert stored['status']=='gotowe_do_odbioru_testowo'
    assert client.post(f'/test/payments/{order["id"]}/events',headers=buyer[0],json=event).status_code==200
    assert client.post(f'/test/orders/{order["id"]}/ready',headers=farmer[0]).status_code==200
    response=client.post(f'/orders/{order["id"]}/confirm',headers=farmer[0],json={'pin':order['pin_test_only']})
    assert response.status_code==200 and response.json()['confirmed']
    assert client.post(f'/orders/{order["id"]}/confirm',headers=farmer[0],json={'pin':order['pin_test_only']}).status_code==409


def test_favorite_catalog_only_returns_available_public_products(actors):
    client,users=actors
    pid=new_product(client,users[0][0])
    assert client.post('/catalog/favorites',json={'ids':[pid,pid,999999999]}).json()['items'][0]['id']==pid
    assert len(client.post('/catalog/favorites',json={'ids':[pid,pid]}).json()['items'])==1
    for invalid in ([True],[1.5],['1'],[-1],list(range(1,202))):
        assert client.post('/catalog/favorites',json={'ids':invalid}).status_code==422
    with module.db() as con:con.execute('UPDATE products SET stock=0 WHERE id=?',(pid,))
    assert client.post('/catalog/favorites',json={'ids':[pid]}).json()['items']==[]


def proposal_body(revision=0):
    day=datetime.now(ZoneInfo('Europe/Warsaw')).date()+timedelta(days=8)
    return {'revision':revision,'delivery_date':str(day),'from_time':'11:00','to_time':'13:00'}


@pytest.mark.parametrize('cart',[False,True])
def test_only_customer_accepts_seller_counterproposal_for_entire_delivery(actors,cart):
    client,users,pid,body=setup(actors)
    farmer,other_farmer,buyer,other_buyer,courier=users
    if cart:
        assert client.put('/cart/items',headers=buyer[0],json={'product_id':pid,'quantity':2}).status_code==200
        second=new_product(client,farmer[0])
        assert client.put('/cart/items',headers=buyer[0],json={'product_id':second,'quantity':1}).status_code==200
        body.pop('product_id');body.pop('quantity')
        result=client.post('/cart/checkout-test',headers={**buyer[0],'Idempotency-Key':uuid4().hex},json=body)
        assert result.status_code==201,result.text
        oid=result.json()['orders'][0]['id']
    else:
        result=client.post('/orders',headers=buyer[0],json=body)
        assert result.status_code==201,result.text
        oid=result.json()['id']
    url=f'/address-delivery/requests/{oid}'
    p=proposal_body()
    assert client.post(url+'/proposals',headers=other_farmer[0],json=p).status_code==404
    assert client.post(url+'/proposals',headers=buyer[0],json=p).status_code==403
    assert client.post(url+'/proposals',headers=farmer[0],json=p).status_code==200
    assert client.post(url+'/proposals',headers=farmer[0],json=p).json()['already_processed']
    assert client.post(url+'/decision',headers=farmer[0],json={'decision':'accepted','revision':1}).status_code==409
    decision={'decision':'accepted','revision':1}
    assert client.post(url+'/proposal-decision',headers=farmer[0],json=decision).status_code==403
    assert client.post(url+'/proposal-decision',headers=other_buyer[0],json=decision).status_code==404
    assert client.post(url+'/proposal-decision',headers=buyer[0],json=decision).status_code==200
    assert client.post(url+'/proposal-decision',headers=buyer[0],json=decision).json()['already_processed']
    with module.db() as con:
        row=con.execute('SELECT * FROM address_delivery_requests WHERE order_id=?',(oid,)).fetchone()
        assert row['state']=='accepted' and row['delivery_date']==p['delivery_date']
        assert row['agreed_from']==660 and row['agreed_to']==780
        if cart:
            rows=con.execute('SELECT r.* FROM address_delivery_requests r JOIN shipment_order_links l ON l.order_id=r.order_id WHERE l.shipment_id=?',(result.json()['shipment_id'],)).fetchall()
            assert len(rows)==2 and all(r['state']=='accepted' and r['delivery_date']==p['delivery_date'] and r['revision']==2 for r in rows)
    assert client.post(f'/test/payments/{oid}/events',headers=buyer[0],json={'event_type':'payment_success_test','event_id':uuid4().hex}).status_code==200


def test_rejected_and_stale_proposal_cannot_change_delivery(actors):
    client,users,_,_,oid=create(actors)
    farmer,buyer=users[0][0],users[2][0]
    url=f'/address-delivery/requests/{oid}'
    assert client.post(url+'/proposals',headers=farmer,json=proposal_body()).status_code==200
    assert client.post(url+'/proposals',headers=farmer,json={**proposal_body(1),'from_time':'13:00','to_time':'15:00'}).status_code==200
    assert client.post(url+'/proposal-decision',headers=buyer,json={'decision':'accepted','revision':1}).status_code==409
    assert client.post(url+'/proposal-decision',headers=buyer,json={'decision':'declined','revision':2}).status_code==200
    with module.db() as con:
        row=con.execute('SELECT * FROM address_delivery_requests WHERE order_id=?',(oid,)).fetchone()
        assert row['state']=='pending' and row['revision']==3 and row['agreed_from']==720
    assert client.post(url+'/decision',headers=farmer,json={'decision':'accepted','revision':3}).status_code==200


def test_invalid_or_expired_counterproposal_never_changes_stock_or_term(actors):
    client,users,_,_,oid=create(actors)
    url=f'/address-delivery/requests/{oid}/proposals'
    assert client.post(url,headers=users[0][0],json={**proposal_body(),'from_time':'14:00','to_time':'12:00'}).status_code==422
    with module.db() as con:con.execute("UPDATE inventory_reservations SET expires_at='2000-01-01T00:00:00+00:00' WHERE order_id=?",(oid,))
    assert client.post(url,headers=users[0][0],json=proposal_body()).status_code==409

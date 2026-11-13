"""Issue 60: reversible offers, immutable prices/reservations and point history."""
from fastapi.testclient import TestClient
from backend import app as api
from tests.test_local_marketplace import setup_market


def exercise_issue60(client, farmer, buyer, product, point, body):
    original=client.get('/products/mine',headers=farmer).json()
    listing=next(p for p in original if p['id']==product)
    quantity=listing['stock']
    order=client.post('/orders',headers=buyer,json={'product_id':product,'quantity':2,'fulfillment':'odbior','pickup_point_id':point})
    assert order.status_code==201,order.text
    order_id=order.json()['order_id'] if 'order_id' in order.json() else order.json()['id']
    before=next(o for o in client.get('/orders/me',headers=buyer).json() if o['id']==order_id)
    stale=client.patch('/products/mine/'+str(product),headers=farmer,json={'stock':quantity,'expected_stock':quantity,'price_grosze':999})
    assert stale.status_code==409
    changed=client.patch('/products/mine/'+str(product),headers=farmer,json={'price_grosze':777,'stock':quantity-2,'expected_stock':quantity-2,'description':'Nowy opis oferty'})
    assert changed.status_code==200,changed.text
    after=next(o for o in client.get('/orders/me',headers=buyer).json() if o['id']==order_id)
    assert after==before
    assert client.delete('/pickup-points/'+str(point),headers=farmer).status_code==409
    inactive=client.put('/pickup-points/'+str(point),headers=farmer,json={**body,'active':False})
    assert inactive.status_code==200
    assert client.put('/pickup-points/'+str(point),headers=farmer,json={**body,'active':False,'street':'Nowa 44'}).status_code==409
    assert client.patch('/products/mine/'+str(product),headers=farmer,json={'listing_active':False}).status_code==200
    assert product not in {p['id'] for p in client.get('/products').json()}
    assert client.post('/catalog/query',json={'q':listing['name']}).json()['total']==0
    assert client.put('/cart/items',headers=buyer,json={'product_id':product,'quantity':1}).status_code==409
    assert client.post('/orders',headers=buyer,json={'product_id':product,'quantity':1,'fulfillment':'dostawa','delivery_city':'Opole','delivery_street':'Polna 1','delivery_postal_code':'45-001'}).status_code==409
    assert client.post('/orders/'+str(order_id)+'/cancel-test',headers=buyer).status_code==200
    mine=next(p for p in client.get('/products/mine',headers=farmer).json() if p['id']==product)
    assert mine['stock']==quantity and mine['listing_active'] is False and mine['price_grosze']==777
    assert client.post('/catalog/query',json={'q':listing['name']}).json()['total']==0
    removed=client.delete('/pickup-points/'+str(point),headers=farmer)
    assert removed.status_code==200 and removed.json()['history_preserved']
    assert next(p for p in client.get('/farmers/me/pickup-points',headers=farmer).json() if p['id']==point)['active']==0
    assert any(o['id']==order_id for o in client.get('/orders/me',headers=buyer).json())
    assert client.patch('/products/mine/'+str(product),headers=farmer,json={'listing_active':True}).status_code==200
    assert client.post('/catalog/query',json={'q':listing['name']}).json()['total']>=1


def test_offer_reservations_price_history_and_point_removal():
    c,f,b,fid,pid,point,body=setup_market(name='Oferta kontrolna sześćdziesiąt')
    exercise_issue60(c,f,b,pid,point,body)


def test_point_and_listing_edits_are_owner_only():
    c,f,b,_,pid,point,body=setup_market()
    c2,other,*_=setup_market()
    assert c.delete('/pickup-points/'+str(point),headers=other).status_code==404
    assert c.delete('/pickup-points/'+str(point),headers=b).status_code==403
    assert c.delete('/pickup-points/'+str(point)).status_code==401
    assert c.patch('/products/mine/'+str(pid),headers=other,json={'listing_active':False}).status_code==404
    assert c.patch('/products/mine/'+str(pid),headers=b,json={'price_grosze':99}).status_code==403
    for fields in [{'price_grosze':1.2},{'stock':-1},{'expected_stock':True},{'listing_active':1}]:
        assert c.patch('/products/mine/'+str(pid),headers=f,json=fields).status_code==422


def test_availability_migration_is_additive_and_repeatable():
    c,f,b,_,pid,point,body=setup_market()
    assert c.patch('/products/mine/'+str(pid),headers=f,json={'listing_active':False}).status_code==200
    with api.db() as con:
        before=[tuple(r) for r in con.execute('SELECT * FROM products ORDER BY id')]
        script=(__import__('pathlib').Path(__file__).resolve().parents[1]/'database/optional_product_listing_states.sql').read_text()
        con.executescript(script);con.executescript(script)
        assert [tuple(r) for r in con.execute('SELECT * FROM products ORDER BY id')]==before
        assert not api.product_listings.active(con,pid)

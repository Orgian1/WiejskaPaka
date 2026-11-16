"""Real HTTP buyer ratings after actual PIN collection, never financial mutations."""
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4
import pytest
from tests.test_purchase_record_http_restart import server
from tests.test_postgres_full_api_optin import register,product


def purchase(client,buyer,seller,pid=None):
    pid=pid or product(client,seller)
    point=client.post('/pickup-points',headers=seller,json={'name':'Punkt ocen','city':'Radom','street':'Polna 1','opening_hours':'8-18'})
    assert point.status_code==201,point.text
    result=client.post('/orders',headers=buyer,json={'product_id':pid,'quantity':1,'fulfillment':'odbior','pickup_point_id':point.json()['id']})
    assert result.status_code==201,result.text
    return result.json()


def collect(client,buyer,seller,order):
    oid=order['id']
    paid=client.post(f'/test/payments/{oid}/events',headers=buyer,json={'event_id':uuid4().hex,'event_type':'payment_success_test'})
    assert paid.status_code==200,paid.text
    assert client.post(f'/test/orders/{oid}/ready',headers=seller).status_code==200
    reply=client.post(f'/orders/{oid}/confirm',headers=seller,json={'pin':order['pin_test_only'],'checked_goods':True})
    assert reply.status_code==200 and reply.json()['confirmed'],reply.text


def exercise(client):
    seller,sid=register(client,'rolnik');buyer,_=register(client,'klient');other,_=register(client,'klient');courier,_=register(client,'dostawca')
    summary=f'/farmers/{sid}/ratings'
    assert client.get(summary).json()=={'farmer_id':sid,'count':0,'average':None}
    order=purchase(client,buyer,seller);oid=order['id'];url=f'/orders/{oid}/seller-rating'
    assert client.post(url,json={'stars':5}).status_code==401
    assert client.post(url,headers=other,json={'stars':5}).status_code==404
    for headers in (seller,courier):assert client.post(url,headers=headers,json={'stars':5}).status_code==403
    assert client.post(url,headers=buyer,json={'stars':5}).status_code==409
    assert client.get(url,headers=other).status_code==404
    assert client.get(url,headers=buyer).json()['stars'] is None
    collect(client,buyer,seller,order)
    before=client.get('/orders/me',headers=buyer).json()
    for value in (0,6,True,'5',3.5):assert client.post(url,headers=buyer,json={'stars':value}).status_code==422
    assert client.post(url,headers=buyer,json={'stars':5,'buyer_id':999}).status_code==422
    # Competing devices may not create or overwrite a second rating.
    with ThreadPoolExecutor(2) as pool:
        replies=list(pool.map(lambda stars:client.post(url,headers=buyer,json={'stars':stars}),[1,5]))
    assert sorted(r.status_code for r in replies)==[200,409],[r.text for r in replies]
    stars=next(r.json()['stars'] for r in replies if r.status_code==200)
    assert client.post(url,headers=buyer,json={'stars':stars}).json()['already_rated']
    assert client.get(url,headers=buyer).json()=={'order_id':oid,'farmer_id':sid,'stars':stars}
    assert client.get('/orders/me',headers=buyer).json()==before
    assert client.get(summary).json()=={'farmer_id':sid,'count':1,'average':stars}
    another=purchase(client,other,seller);collect(client,other,seller,another)
    assert client.post(f'/orders/{another["id"]}/seller-rating',headers=other,json={'stars':3}).status_code==200
    public=client.get(summary).json()
    assert public=={'farmer_id':sid,'count':2,'average':(stars+3)/2}
    assert set(public)=={'farmer_id','count','average'}
    assert client.get(f'/orders/{another["id"]}/seller-rating',headers=buyer).status_code==404
    cancelled=purchase(client,buyer,seller)
    assert client.post(f'/orders/{cancelled["id"]}/cancel-test',headers=buyer).status_code==200
    assert client.post(f'/orders/{cancelled["id"]}/seller-rating',headers=buyer,json={'stars':5}).status_code==409
    assert client.post('/auth/logout',headers=buyer).status_code==200
    assert client.get(url,headers=buyer).status_code==401
    return sid


def test_rating_http_persists_and_remains_private(tmp_path):
    path=tmp_path/'ratings.sqlite3'
    with server(path) as client:sid=exercise(client)
    with server(path) as client:assert client.get(f'/farmers/{sid}/ratings').json()['count']==2

"""Account isolation and distinct position counts, including completed orders."""
from fastapi.testclient import TestClient
from backend import app as module
from tests.test_product_categories_http import account


def exercise_navigation_counts(client):
    farmer=account(client,'rolnik');other_farmer=account(client,'rolnik');buyer=account(client,'klient');other_buyer=account(client,'klient');courier=account(client,'dostawca')
    ids=[]
    for name in ['Towar A','Towar B']:
        p=client.post('/products',headers=farmer,json={'name':name,'stock':30,'price_grosze':299,'delivery_grosze':0});assert p.status_code==201;ids.append(p.json()['id'])
    url='/account/navigation-counts'
    assert client.get(url).status_code==401 and client.get(url,headers=courier).status_code==403
    for _ in range(2):assert client.put('/favorites/'+str(ids[0]),headers=buyer).status_code==200
    assert client.put('/cart/items',headers=buyer,json={'product_id':ids[0],'quantity':7}).status_code==200
    assert client.put('/cart/items',headers=buyer,json={'product_id':ids[1],'quantity':2}).status_code==200
    assert client.get(url,headers=buyer).json()=={'favorites_count':1,'cart_count':2,'current_orders_count':0}
    assert client.get(url,headers=other_buyer).json()=={'favorites_count':0,'cart_count':0,'current_orders_count':0}
    point=client.post('/pickup-points',headers=farmer,json={'name':'Licznik','city':'Warszawa','street':'Testowa 1','opening_hours':'9-16'});assert point.status_code==201
    order=client.post('/orders',headers=buyer,json={'product_id':ids[0],'quantity':1,'fulfillment':'odbior','pickup_point_id':point.json()['id']});assert order.status_code==201
    assert client.get(url,headers=farmer).json()['current_orders_count']==1
    assert client.get(url,headers=other_farmer).json()['current_orders_count']==0
    assert client.post('/orders/'+str(order.json()['id'])+'/cancel-test',headers=buyer).status_code==200
    assert client.get(url,headers=farmer).json()['current_orders_count']==0
    assert client.delete('/favorites/'+str(ids[0]),headers=buyer).status_code==200
    assert client.delete('/cart/items/'+str(ids[0]),headers=buyer).status_code==200
    assert client.get(url,headers=buyer).json()=={'favorites_count':0,'cart_count':1,'current_orders_count':0}


def test_counts_are_private_idempotent_and_count_positions_not_quantities():
    exercise_navigation_counts(TestClient(module.app))

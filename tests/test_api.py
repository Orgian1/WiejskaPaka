import os
import tempfile
from pathlib import Path
p=Path(tempfile.mkdtemp())/'test.sqlite3'
os.environ['WIEJSKAPAKA_DB']=str(p)
from fastapi.testclient import TestClient
from backend.app import app
from backend.money import split_75_20_5, full_refund
c=TestClient(app)
def reg(email,role):
    assert c.post('/auth/register',json={'email':email,'password':'bardzo-bezpieczne-haslo-123','role':role}).status_code==201
    r=c.post('/auth/login',json={'email':email,'password':'bardzo-bezpieczne-haslo-123'})
    assert r.status_code==200
    return {'Authorization':'Bearer '+r.json()['access_token']}

def test_flow():
    farmer=reg('farmer@example.com','rolnik')
    buyer=reg('buyer@example.com','klient')
    other=reg('other@example.com','rolnik')
    assert c.post('/products',json={'name':'Jabłka','price_grosze':999,'delivery_grosze':501,'stock':2},headers=buyer).status_code==403
    product=c.post('/products',json={'name':'Jabłka','price_grosze':999,'delivery_grosze':501,'stock':2},headers=farmer).json()['id']
    point=c.post('/pickup-points',json={'name':'Gospodarstwo','city':'Radom','street':'Polna 2','opening_hours':'8-16'},headers=farmer).json()['id']
    order=c.post('/orders',json={'product_id':product,'quantity':2,'fulfillment':'odbior','pickup_point_id':point},headers=buyer)
    assert order.status_code==201
    order=order.json()
    assert order['total_grosze']==1998
    assert c.post('/orders',json={'product_id':product,'quantity':1,'fulfillment':'odbior','pickup_point_id':point},headers=buyer).status_code==409
    assert c.post(f'/test/orders/{order["id"]}/ready',headers=other).status_code==404
    assert c.post(f'/test/orders/{order["id"]}/ready',headers=farmer).status_code==200
    assert c.post(f'/orders/{order["id"]}/confirm',json={'pin':order['pin_test_only'],'checked_goods':True},headers=buyer).status_code==403
    assert c.post(f'/orders/{order["id"]}/confirm',json={'pin':order['pin_test_only'],'checked_goods':True},headers=other).status_code==403
    bad=c.post(f'/orders/{order["id"]}/confirm',json={'pin':'999999' if order['pin_test_only']!='999999' else '888888','checked_goods':True},headers=farmer)
    assert bad.json()['confirmed'] is False
    good=c.post(f'/orders/{order["id"]}/confirm',json={'pin':order['pin_test_only'],'checked_goods':True},headers=farmer)
    assert good.json()['confirmed'] is True
    assert c.post(f'/orders/{order["id"]}/confirm',json={'pin':order['pin_test_only'],'checked_goods':True},headers=farmer).status_code==409

def test_money():
    for amount in range(10000):
        x=split_75_20_5(amount)
        assert sum(x)==amount
        assert full_refund(amount)==amount
    assert split_75_20_5(9999)==(7499,2000,500)

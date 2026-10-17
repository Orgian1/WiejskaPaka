import os
import tempfile
from pathlib import Path
os.environ['WIEJSKAPAKA_DB'] = str(Path(tempfile.mkdtemp())/'shipment_pin.sqlite3')
from fastapi.testclient import TestClient
from backend.app import app, db, token_hash
from datetime import datetime, timezone, timedelta


def test_single_pin_confirms_entire_shipment_and_blocks_individual_confirmation():
    client = TestClient(app)
    with db() as con:
        for uid, role in [(581,'rolnik'),(582,'klient')]:
            con.execute('INSERT INTO users(id,email,password_hash,role) VALUES(?,?,?,?)',(uid,f'test{uid}@example.org','x',role))
            con.execute('INSERT INTO sessions(token_hash,user_id,expires_at) VALUES(?,?,?)',(token_hash(f'token-{uid}'),uid,(datetime.now(timezone.utc)+timedelta(hours=1)).isoformat()))
        for pid in (581,582):
            con.execute('INSERT INTO products(id,farmer_id,name,price_grosze,delivery_grosze,stock) VALUES(?,?,?,?,?,?)',(pid,581,'Test',1000,200,3))
            con.execute('INSERT INTO saved_cart_items(buyer_id,product_id,quantity) VALUES(?,?,?)',(582,pid,1))
        con.execute('INSERT INTO pickup_points(id,farmer_id,name,city,street,opening_hours,active) VALUES(?,?,?,?,?,?,?)',(581,581,'Punkt','Miasto','Ulica 1','9-17',1))
    buyer={'Authorization':'Bearer token-582'}
    seller={'Authorization':'Bearer token-581'}
    response=client.post('/cart/checkout-test',headers=buyer,json={'fulfillment':'odbior','pickup_point_id':581})
    assert response.status_code==201,response.text
    data=response.json()
    assert len(data['orders'])==2
    assert 'pin_test_only' not in data['orders'][0]
    pin=data['shipment_pin_test_only']
    with db() as con:
        for order in data['orders']:
            con.execute("UPDATE orders SET status='gotowe_do_odbioru_testowo' WHERE id=?",(order['id'],))
    individual=client.post(f"/orders/{data['orders'][0]['id']}/confirm",headers=seller,json={'pin':pin,'checked_goods':True})
    assert individual.status_code==409
    wrong=client.post(f"/shipments/{data['shipment_id']}/confirm",headers=seller,json={'pin':'000000' if pin!='000000' else '000001','checked_goods':True})
    assert wrong.status_code==200 and wrong.json()['confirmed'] is False
    ok=client.post(f"/shipments/{data['shipment_id']}/confirm",headers=seller,json={'pin':pin,'checked_goods':True})
    assert ok.status_code==200,ok.text
    assert ok.json()['confirmed_orders']==2
    with db() as con:
        assert con.execute("SELECT COUNT(*) AS n FROM orders WHERE status='odebrane' AND pin_used=1").fetchone()['n']==2
    assert client.post(f"/shipments/{data['shipment_id']}/confirm",headers=seller,json={'pin':pin,'checked_goods':True}).status_code==409


def test_farmer_shipment_listing_and_role_isolation():
    client = TestClient(app)
    seller = client.get('/shipments/farmer/mine', headers={'Authorization':'Bearer token-581'})
    assert seller.status_code == 200, seller.text
    assert len(seller.json()['shipments']) == 1
    shipment = seller.json()['shipments'][0]
    assert shipment['item_count'] == 2
    assert shipment['delivery_grosze'] == 0
    assert shipment['total_grosze'] == 2000
    buyer = client.get('/shipments/farmer/mine', headers={'Authorization':'Bearer token-582'})
    assert buyer.status_code == 403
    mine = client.get('/shipments/mine', headers={'Authorization':'Bearer token-582'})
    assert mine.status_code == 200 and len(mine.json()['shipments']) == 1

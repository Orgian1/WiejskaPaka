import os
import tempfile
from pathlib import Path
os.environ['WIEJSKAPAKA_DB'] = str(Path(tempfile.mkdtemp()) / 'courier_shipments.sqlite3')
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from backend.app import app, db, token_hash


def test_entire_shipment_courier_flow():
    client = TestClient(app)
    with db() as con:
        for uid, role in [(621, 'rolnik'), (622, 'klient'), (623, 'dostawca'), (624, 'rolnik')]:
            con.execute('INSERT INTO users(id,email,password_hash,role) VALUES(?,?,?,?)', (uid, f'b621-{uid}@example.org', 'x', role))
            con.execute('INSERT INTO sessions(token_hash,user_id,expires_at) VALUES(?,?,?)', (token_hash(f'b621-{uid}'), uid, (datetime.now(timezone.utc)+timedelta(hours=1)).isoformat()))
        for pid in (621, 622):
            con.execute('INSERT INTO products(id,farmer_id,name,price_grosze,delivery_grosze,stock) VALUES(?,?,?,?,?,?)', (pid,621,'Towar',1000,250,5))
            con.execute('INSERT INTO saved_cart_items(buyer_id,product_id,quantity) VALUES(?,?,?)',(622,pid,1))
    headers=lambda uid: {'Authorization':f'Bearer b621-{uid}'}
    response=client.post('/cart/checkout-test',headers=headers(622),json={'fulfillment':'dostawa','delivery_city':'Warszawa','delivery_street':'Testowa 1','delivery_postal_code':'00-001'})
    assert response.status_code==201,response.text
    shipment=response.json()['shipment_id']
    assert response.json()['total_grosze']==2250
    assert client.post(f'/shipments/{shipment}/assign-courier-test',headers=headers(624),json={'courier_id':623}).status_code==404
    assigned=client.post(f'/shipments/{shipment}/assign-courier-test',headers=headers(621),json={'courier_id':623})
    assert assigned.status_code==200,assigned.text
    assert assigned.json()['assigned_orders']==2
    courier=client.get('/couriers/me/shipments',headers=headers(623))
    assert courier.status_code==200 and courier.json()['shipments'][0]['item_count']==2
    dispatched=client.post(f'/shipments/{shipment}/dispatch-test',headers=headers(621))
    assert dispatched.status_code==200,dispatched.text
    assert dispatched.json()['dispatched_orders']==2
    confirmed=client.post(f'/shipments/{shipment}/confirm',headers=headers(623),json={'pin':response.json()['shipment_pin_test_only'],'checked_goods':True})
    assert confirmed.status_code==200 and confirmed.json()['confirmed_orders']==2,confirmed.text
    with db() as con:
        assert con.execute("SELECT COUNT(*) AS n FROM orders WHERE status='odebrane'").fetchone()['n']==2

import os
import tempfile
from pathlib import Path
os.environ['WIEJSKAPAKA_DB'] = str(Path(tempfile.mkdtemp())/'shipment_links.sqlite3')
from fastapi.testclient import TestClient
from backend.app import app, db, token_hash
from datetime import datetime, timezone, timedelta


def test_one_shipment_multiple_order_rows_and_private_listing():
    client = TestClient(app)
    with db() as con:
        con.execute("INSERT INTO users(id,email,password_hash,role) VALUES(561,'seller561@test.pl','x','rolnik')")
        con.execute("INSERT INTO users(id,email,password_hash,role) VALUES(562,'buyer562@test.pl','x','klient')")
        con.execute("INSERT INTO users(id,email,password_hash,role) VALUES(563,'buyer563@test.pl','x','klient')")
        for uid in (562,563):
            con.execute('INSERT INTO sessions(token_hash,user_id,expires_at) VALUES(?,?,?)',
                        (token_hash(f'b561-{uid}'),uid,(datetime.now(timezone.utc)+timedelta(hours=1)).isoformat()))
        for pid in (561,562):
            con.execute('INSERT INTO products(id,farmer_id,name,price_grosze,delivery_grosze,stock) VALUES(?,?,?,?,?,?)',
                        (pid,561,'Test',1000,300,5))
            con.execute('INSERT INTO saved_cart_items(buyer_id,product_id,quantity) VALUES(?,?,?)',(562,pid,1))
    h={'Authorization':'Bearer b561-562'}
    response=client.post('/cart/checkout-test',headers=h,json={'fulfillment':'dostawa','delivery_city':'Warszawa','delivery_street':'Testowa 1','delivery_postal_code':'00-001'})
    assert response.status_code==201,response.text
    data=response.json()
    assert len(data['orders'])==2 and data['delivery_grosze']==300
    with db() as con:
        links=con.execute('SELECT shipment_id FROM shipment_order_links ORDER BY order_id').fetchall()
        assert len(links)==2 and links[0]['shipment_id']==links[1]['shipment_id']==data['shipment_id']
        assert con.execute('SELECT SUM(delivery_grosze) AS total FROM orders').fetchone()['total']==300
    mine=client.get('/shipments/mine',headers=h)
    assert mine.status_code==200 and mine.json()['shipments'][0]['item_count']==2
    other=client.get('/shipments/mine',headers={'Authorization':'Bearer b561-563'})
    assert other.status_code==200 and other.json()['shipments']==[]

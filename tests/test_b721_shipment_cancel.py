import os
import tempfile
from pathlib import Path
os.environ['WIEJSKAPAKA_DB'] = str(Path(tempfile.mkdtemp()) / 'cancel_shipment.sqlite3')
from fastapi.testclient import TestClient
from backend.app import app, db, token_hash
from datetime import datetime, timezone, timedelta


def test_cancel_whole_shipment_and_restore_stock():
    client = TestClient(app)
    with db() as con:
        con.execute("INSERT INTO users(id,email,password_hash,role) VALUES(721,'seller721@test.pl','x','rolnik')")
        for uid in (722, 723):
            con.execute('INSERT INTO users(id,email,password_hash,role) VALUES(?,?,?,?)',
                        (uid, f'buyer{uid}@test.pl', 'x', 'klient'))
            con.execute('INSERT INTO sessions(token_hash,user_id,expires_at) VALUES(?,?,?)',
                        (token_hash(f'b721-{uid}'), uid, (datetime.now(timezone.utc)+timedelta(hours=1)).isoformat()))
        for pid in (721, 722):
            con.execute('INSERT INTO products(id,farmer_id,name,price_grosze,delivery_grosze,stock) VALUES(?,?,?,?,?,?)',
                        (pid, 721, 'Produkt', 1000, 250, 4))
            con.execute('INSERT INTO saved_cart_items(buyer_id,product_id,quantity) VALUES(?,?,?)', (722,pid,2))
    buyer = {'Authorization':'Bearer b721-722'}
    r = client.post('/cart/checkout-test',headers=buyer,json={'fulfillment':'dostawa','delivery_city':'Warszawa','delivery_street':'Testowa 1','delivery_postal_code':'00-001'})
    assert r.status_code == 201, r.text
    data=r.json()
    assert data['total_grosze']==4250
    assert client.post(f'/orders/{data["orders"][0]["id"]}/cancel-test',headers=buyer).status_code==409
    assert client.post(f'/shipments/{data["shipment_id"]}/cancel-test',headers={'Authorization':'Bearer b721-723'}).status_code==404
    ok=client.post(f'/shipments/{data["shipment_id"]}/cancel-test',headers=buyer)
    assert ok.status_code==200,ok.text
    assert ok.json()['cancelled_orders']==2
    assert client.post(f'/shipments/{data["shipment_id"]}/cancel-test',headers=buyer).status_code==409
    with db() as con:
        assert [r['stock'] for r in con.execute('SELECT stock FROM products WHERE id IN (721,722) ORDER BY id')]==[4,4]
        assert [r['status'] for r in con.execute('SELECT status FROM orders ORDER BY id')]==['anulowane_testowo']*2

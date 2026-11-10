import os
import tempfile
from pathlib import Path
os.environ['WIEJSKAPAKA_DB'] = str(Path(tempfile.mkdtemp()) / 'details.sqlite3')
os.environ['WP_ENABLE_TEST_PAYMENTS'] = '1'
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from backend.app import app, db, token_hash


def test_shipment_details_permissions_and_one_delivery():
    client = TestClient(app)
    with db() as con:
        for uid, role in [(681, 'rolnik'), (682, 'klient'), (683, 'dostawca'), (684, 'klient'), (685,'rolnik')]:
            con.execute('INSERT INTO users(id,email,password_hash,role) VALUES(?,?,?,?)',
                        (uid, f'b681-{uid}@example.org', 'x', role))
            con.execute('INSERT INTO sessions(token_hash,user_id,expires_at) VALUES(?,?,?)',
                        (token_hash(f'b681-{uid}'),uid,(datetime.now(timezone.utc)+timedelta(hours=1)).isoformat()))
        for pid in (681,682):
            con.execute('INSERT INTO products(id,farmer_id,name,price_grosze,delivery_grosze,stock) VALUES(?,?,?,?,?,?)',
                        (pid,681,'Towar',1000,250,5))
            con.execute('INSERT INTO saved_cart_items(buyer_id,product_id,quantity) VALUES(?,?,?)',(682,pid,1))
    h=lambda uid:{'Authorization':f'Bearer b681-{uid}'}
    checkout=client.post('/cart/checkout-test',headers=h(682),json={'fulfillment':'dostawa','delivery_city':'Warszawa','delivery_street':'Testowa 1','delivery_postal_code':'00-001'})
    assert checkout.status_code==201,checkout.text
    sid=checkout.json()['shipment_id']
    url=f'/shipments/{sid}/details'
    for uid in (682,681):
        r=client.get(url,headers=h(uid))
        assert r.status_code==200,r.text
        d=r.json()
        assert d['total_grosze']==2250
        assert d['delivery_grosze']==250
        assert d['refund_test_grosze']==0
        assert len(d['items'])==2
        assert sum(x['delivery_grosze'] for x in d['items'])==250
        assert 'delivery_street' not in str(d)
    for uid in (684,685,683):
        assert client.get(url,headers=h(uid)).status_code==404
    assert client.post(f'/shipments/{sid}/assign-courier-test',headers=h(681),json={'courier_id':683}).status_code==200
    courier=client.get(url,headers=h(683))
    assert courier.status_code==200,courier.text
    assert courier.json()['refund_test_grosze'] is None

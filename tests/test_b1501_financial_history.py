import os
import tempfile
from pathlib import Path
os.environ['WIEJSKAPAKA_DB'] = str(Path(tempfile.mkdtemp()) / 'history.sqlite3')
os.environ['WP_ENABLE_TEST_PAYMENTS'] = '1'
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from backend.app import app, db, token_hash


def test_private_financial_history_and_one_delivery():
    client = TestClient(app)
    with db() as con:
        for uid, role in [(1501,'rolnik'), (1502,'klient'), (1503,'klient')]:
            con.execute('INSERT INTO users(id,email,password_hash,role) VALUES(?,?,?,?)',
                        (uid,f'b1501-{uid}@example.org','x',role))
            con.execute('INSERT INTO sessions(token_hash,user_id,expires_at) VALUES(?,?,?)',
                        (token_hash(f'b1501-{uid}'),uid,(datetime.now(timezone.utc)+timedelta(hours=1)).isoformat()))
        for pid in (1501,1502):
            con.execute('INSERT INTO products(id,farmer_id,name,price_grosze,delivery_grosze,stock) VALUES(?,?,?,?,?,?)',
                        (pid,1501,'Produkt',1000,250,5))
            con.execute('INSERT INTO saved_cart_items(buyer_id,product_id,quantity) VALUES(?,?,?)',(1502,pid,1))
    headers=lambda uid:{'Authorization':f'Bearer b1501-{uid}'}
    result=client.post('/cart/checkout-test',headers=headers(1502),json={
        'fulfillment':'dostawa','delivery_city':'Warszawa',
        'delivery_street':'Testowa 1','delivery_postal_code':'00-001'})
    assert result.status_code==201,result.text
    sid=result.json()['shipment_id']
    url=f'/shipments/{sid}/financial-history-test'
    assert client.get(url,headers=headers(1503)).status_code==404
    assert client.get(url,headers=headers(1501)).status_code==403
    data=client.get(url,headers=headers(1502))
    assert data.status_code==200,data.text
    payload=data.json()
    assert payload['total_grosze']==2250
    assert payload['delivery_grosze']==250
    assert payload['products_grosze']==2000
    assert payload['refund_grosze']==0
    assert payload['delivery_consistent'] is True
    assert len(payload['orders'])==2
    assert sum(o['delivery_grosze'] for o in payload['orders'])==250
    assert 'Testowa' not in data.text
    assert 'token_hash' not in data.text
    assert 'event_id' not in data.text

import os
import tempfile
from pathlib import Path
os.environ['WIEJSKAPAKA_DB'] = str(Path(tempfile.mkdtemp())/'multi.sqlite3')
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from backend.app import app, db, token_hash

def test_checkout_selected_seller_keeps_other_sellers_cart():
    c=TestClient(app)
    with db() as con:
        for i,role in [(801,'rolnik'),(802,'rolnik'),(803,'klient')]:
            con.execute('INSERT INTO users(id,email,password_hash,role) VALUES(?,?,?,?)',(i,f'u{i}@test.pl','x',role))
        con.execute('INSERT INTO sessions(token_hash,user_id,expires_at) VALUES(?,?,?)',(token_hash('multibuyer'),803,(datetime.now(timezone.utc)+timedelta(hours=1)).isoformat()))
        for i in (801,802):
            con.execute('INSERT INTO products(id,farmer_id,name,price_grosze,delivery_grosze,stock) VALUES(?,?,?,?,?,?)',(i,i,'Jabłka',1000,100,4))
            con.execute('INSERT INTO saved_cart_items(buyer_id,product_id,quantity) VALUES(?,?,?)',(803,i,2))
    h={'Authorization':'Bearer multibuyer'}
    p={'farmer_id':801,'fulfillment':'dostawa','delivery_city':'Kraków','delivery_street':'Polna 1','delivery_postal_code':'30-001'}
    r=c.post('/cart/checkout-test',json=p,headers=h)
    assert r.status_code==201,r.text
    assert r.json()['total_grosze']==2100
    with db() as con:
        assert [x['product_id'] for x in con.execute('SELECT product_id FROM saved_cart_items WHERE buyer_id=803')]==[802]
        assert con.execute('SELECT stock FROM products WHERE id=801').fetchone()['stock']==2
        assert con.execute('SELECT stock FROM products WHERE id=802').fetchone()['stock']==4
    assert c.post('/cart/checkout-test',json=p,headers=h).status_code==409

import os
import tempfile
from pathlib import Path
os.environ['WIEJSKAPAKA_DB'] = str(Path(tempfile.mkdtemp())/'checkout.sqlite3')
from fastapi.testclient import TestClient
from backend.app import app, db, token_hash
from datetime import datetime, timezone, timedelta

def test_checkout_atomic_stock_and_cart():
    client = TestClient(app)
    with db() as con:
        con.execute("INSERT INTO users(id,email,password_hash,role) VALUES(401,'farmer401@test.pl','x','rolnik')")
        con.execute("INSERT INTO users(id,email,password_hash,role) VALUES(402,'buyer402@test.pl','x','klient')")
        con.execute('INSERT INTO sessions(token_hash,user_id,expires_at) VALUES(?,?,?)',
                    (token_hash('checkout-402'),402,(datetime.now(timezone.utc)+timedelta(hours=1)).isoformat()))
        for i in (401,402):
            con.execute('INSERT INTO products(id,farmer_id,name,price_grosze,delivery_grosze,stock) VALUES(?,?,?,?,?,?)',
                        (i,401,'Produkt',1000,200,3))
    headers={'Authorization':'Bearer checkout-402'}
    for i in (401,402):
        assert client.put('/cart/items',json={'product_id':i,'quantity':2},headers=headers).status_code==200
    payload={'fulfillment':'dostawa','delivery_city':'Warszawa','delivery_street':'Testowa 1','delivery_postal_code':'00-001'}
    result=client.post('/cart/checkout-test',json=payload,headers=headers)
    assert result.status_code==201, result.text
    assert result.json()['total_grosze']==4200
    assert len(result.json()['orders'])==2
    assert client.get('/cart/items',headers=headers).json()['items']==[]
    with db() as con:
        assert con.execute('SELECT COUNT(*) AS n FROM orders WHERE buyer_id=402').fetchone()['n']==2
        assert con.execute('SELECT SUM(stock) AS n FROM products WHERE id IN (401,402)').fetchone()['n']==2
    assert client.post('/cart/checkout-test',json=payload,headers=headers).status_code==409

def test_checkout_rolls_back_on_invalid_stock():
    client=TestClient(app)
    with db() as con:
        con.execute("INSERT INTO users(id,email,password_hash,role) VALUES(411,'farmer411@test.pl','x','rolnik')")
        con.execute("INSERT INTO users(id,email,password_hash,role) VALUES(412,'buyer412@test.pl','x','klient')")
        con.execute('INSERT INTO sessions(token_hash,user_id,expires_at) VALUES(?,?,?)',
                    (token_hash('checkout-412'),412,(datetime.now(timezone.utc)+timedelta(hours=1)).isoformat()))
        con.execute("INSERT INTO products(id,farmer_id,name,price_grosze,delivery_grosze,stock) VALUES(411,411,'Produkt',1000,200,1)")
        con.execute('INSERT INTO saved_cart_items(buyer_id,product_id,quantity) VALUES(412,411,2)')
    headers={'Authorization':'Bearer checkout-412'}
    result=client.post('/cart/checkout-test',json={'fulfillment':'dostawa','delivery_city':'Warszawa','delivery_street':'Testowa 1','delivery_postal_code':'00-001'},headers=headers)
    assert result.status_code==409
    with db() as con:
        assert con.execute('SELECT COUNT(*) AS n FROM orders WHERE buyer_id=412').fetchone()['n']==0
        assert con.execute('SELECT COUNT(*) AS n FROM saved_cart_items WHERE buyer_id=412').fetchone()['n']==1

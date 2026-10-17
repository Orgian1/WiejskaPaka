import os
import tempfile
from pathlib import Path

os.environ['WIEJSKAPAKA_DB'] = str(Path(tempfile.mkdtemp()) / 'cart.sqlite3')
from fastapi.testclient import TestClient
from backend.app import app, db, token_hash
from datetime import datetime, timezone, timedelta

client = TestClient(app)

def test_quote_and_no_stock_change():
    with db() as con:
        con.execute("INSERT INTO users(id,email,password_hash,role) VALUES(1,'farmer@demo.pl','x','rolnik')")
        con.execute("INSERT INTO users(id,email,password_hash,role) VALUES(2,'buyer@demo.pl','x','klient')")
        con.execute("INSERT INTO products(id,farmer_id,name,price_grosze,delivery_grosze,stock) VALUES(1,1,'Jabłka',199,500,10)")
        con.execute("INSERT INTO products(id,farmer_id,name,price_grosze,delivery_grosze,stock) VALUES(2,1,'Gruszki',101,300,10)")
        con.execute('INSERT INTO sessions(token_hash,user_id,expires_at) VALUES(?,?,?)', (token_hash('test-cart'),2,(datetime.now(timezone.utc)+timedelta(hours=1)).isoformat()))
    headers={'Authorization':'Bearer test-cart'}
    payload={'items':[{'product_id':1,'quantity':2},{'product_id':2,'quantity':1}],'fulfillment':'dostawa'}
    response=client.post('/cart/quote',json=payload,headers=headers)
    assert response.status_code==200, response.text
    assert response.json()['total_grosze']==999
    assert response.json()['indicative'] is True
    assert client.post('/cart/quote',json={**payload,'fulfillment':'odbior'},headers=headers).json()['total_grosze']==499
    assert client.post('/cart/quote',json={'items':[{'product_id':1,'quantity':11}],'fulfillment':'odbior'},headers=headers).status_code==409
    assert client.post('/cart/quote',json={'items':[{'product_id':1,'quantity':1},{'product_id':1,'quantity':1}],'fulfillment':'odbior'},headers=headers).status_code==422
    with db() as con:
        assert con.execute('SELECT stock FROM products WHERE id=1').fetchone()['stock']==10

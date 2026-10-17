import os
import tempfile
from pathlib import Path
os.environ['WIEJSKAPAKA_DB'] = str(Path(tempfile.mkdtemp())/'saved.sqlite3')
from fastapi.testclient import TestClient
from backend.app import app, db, token_hash
from datetime import datetime, timezone, timedelta

def test_saved_cart_owner_and_stock():
    client=TestClient(app)
    with db() as con:
        con.execute("INSERT INTO users(id,email,password_hash,role) VALUES(101,'f371@demo.pl','x','rolnik')")
        for i in (102,103):
            con.execute('INSERT INTO users(id,email,password_hash,role) VALUES(?,?,?,?)',(i,f'c{i}@demo.pl','x','klient'))
            con.execute('INSERT INTO sessions(token_hash,user_id,expires_at) VALUES(?,?,?)',(token_hash(f't371-{i}'),i,(datetime.now(timezone.utc)+timedelta(hours=1)).isoformat()))
        con.execute("INSERT INTO products(id,farmer_id,name,price_grosze,delivery_grosze,stock) VALUES(101,101,'Miód',2000,500,3)")
    a={'Authorization':'Bearer t371-102'}
    b={'Authorization':'Bearer t371-103'}
    assert client.put('/cart/items',json={'product_id':101,'quantity':2},headers=a).status_code==200
    assert client.put('/cart/items',json={'product_id':101,'quantity':4},headers=a).status_code==409
    assert client.get('/cart/items',headers=a).json()['items'][0]['quantity']==2
    assert client.get('/cart/items',headers=b).json()['items']==[]
    assert client.delete('/cart/items/101',headers=b).status_code==200
    assert len(client.get('/cart/items',headers=a).json()['items'])==1
    assert client.delete('/cart/items',headers=a).status_code==200
    assert client.get('/cart/items',headers=a).json()['items']==[]
    with db() as con:
        assert con.execute('SELECT stock FROM products WHERE id=101').fetchone()['stock']==3

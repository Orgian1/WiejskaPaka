"""Concurrent buyers cannot reserve the same final unit twice (SQLite)."""
import os
import tempfile
from pathlib import Path
os.environ['DATABASE_URL'] = ''
os.environ['WIEJSKAPAKA_DB'] = str(Path(tempfile.mkdtemp()) / 'concurrent.sqlite3')
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from backend.app import app, db, token_hash


def test_two_buyers_one_unit_only_one_checkout_succeeds():
    with db() as con:
        con.execute("INSERT INTO users(id,email,password_hash,role) VALUES(?,?,?,?)", (18011,'farmer1801@test.local','x','rolnik'))
        con.execute("INSERT INTO products(id,farmer_id,name,price_grosze,delivery_grosze,stock) VALUES(?,?,?,?,?,?)", (18012,18011,'Ostatni produkt',1234,199,1))
        for buyer in (18013,18014):
            con.execute("INSERT INTO users(id,email,password_hash,role) VALUES(?,?,?,?)", (buyer,f'buyer{buyer}@test.local','x','klient'))
            con.execute("INSERT INTO sessions(token_hash,user_id,expires_at) VALUES(?,?,?)", (token_hash(f'auth-{buyer}'),buyer,(datetime.now(timezone.utc)+timedelta(hours=1)).isoformat()))
            con.execute("INSERT INTO saved_cart_items(buyer_id,product_id,quantity) VALUES(?,?,?)", (buyer,18012,1))
    payload={'farmer_id':18011,'fulfillment':'dostawa','delivery_city':'Kraków','delivery_street':'Polna 2','delivery_postal_code':'30-001'}
    def buy(buyer):
        with TestClient(app) as client:
            return client.post('/cart/checkout-test',headers={'Authorization':f'Bearer auth-{buyer}','Idempotency-Key':f'concurrent-key-{buyer}'},json=payload)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(buy,(18013,18014)))
    assert sorted(r.status_code for r in results)==[201,409],[(r.status_code,r.text) for r in results]
    success=next(r.json() for r in results if r.status_code==201)
    assert success['total_grosze']==1433
    assert success['delivery_grosze']==199
    with db() as con:
        assert con.execute('SELECT stock FROM products WHERE id=18012').fetchone()['stock']==0
        assert con.execute('SELECT COUNT(*) AS n FROM shipment_groups WHERE farmer_id=18011').fetchone()['n']==1
        assert con.execute('SELECT COUNT(*) AS n FROM orders WHERE buyer_id IN (18013,18014)').fetchone()['n']==1
        assert con.execute('SELECT COUNT(*) AS n FROM checkout_idempotency WHERE buyer_id IN (18013,18014)').fetchone()['n']==1


def test_concurrent_replay_same_key_returns_identical_shipment():
    with db() as con:
        con.execute("INSERT INTO users(id,email,password_hash,role) VALUES(?,?,?,?)", (18021,'farmer1802@test.local','x','rolnik'))
        con.execute("INSERT INTO products(id,farmer_id,name,price_grosze,delivery_grosze,stock) VALUES(?,?,?,?,?,?)", (18022,18021,'Zapas',1000,300,5))
        con.execute("INSERT INTO users(id,email,password_hash,role) VALUES(?,?,?,?)", (18023,'buyer1802@test.local','x','klient'))
        con.execute("INSERT INTO sessions(token_hash,user_id,expires_at) VALUES(?,?,?)", (token_hash('auth-18023'),18023,(datetime.now(timezone.utc)+timedelta(hours=1)).isoformat()))
        con.execute("INSERT INTO saved_cart_items(buyer_id,product_id,quantity) VALUES(?,?,?)", (18023,18022,2))
    payload={'farmer_id':18021,'fulfillment':'dostawa','delivery_city':'Kraków','delivery_street':'Polna 2','delivery_postal_code':'30-001'}
    def buy(_):
        with TestClient(app) as client:
            return client.post('/cart/checkout-test',headers={'Authorization':'Bearer auth-18023','Idempotency-Key':'replay-concurrent-18023'},json=payload)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(buy,range(2)))
    assert all(r.status_code==201 for r in results),[(r.status_code,r.text) for r in results]
    assert results[0].json()==results[1].json()
    assert results[0].json()['total_grosze']==2300
    with db() as con:
        assert con.execute('SELECT stock FROM products WHERE id=18022').fetchone()['stock']==3
        assert con.execute('SELECT COUNT(*) AS n FROM shipment_groups WHERE farmer_id=18021').fetchone()['n']==1

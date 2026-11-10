"""Regression: multi-line stock exhaustion and idempotent checkout replay."""
import os
import tempfile
from pathlib import Path
os.environ['DATABASE_URL'] = ''
os.environ['WIEJSKAPAKA_DB'] = str(Path(tempfile.mkdtemp()) / 'multiline.sqlite3')
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from backend.app import app, db, token_hash


def setup_cart():
    with db() as con:
        con.execute('INSERT INTO users(id,email,password_hash,role) VALUES(?,?,?,?)', (112811,'farm11281@test.local','x','rolnik'))
        for product, stock in [(112812, 2), (112813, 1)]:
            con.execute('INSERT INTO products(id,farmer_id,name,price_grosze,delivery_grosze,stock) VALUES(?,?,?,?,?,?)', (product,112811,str(product),1000,250,stock))
        for buyer in (112814,112815):
            con.execute('INSERT INTO users(id,email,password_hash,role) VALUES(?,?,?,?)', (buyer,f'b{buyer}@test.local','x','klient'))
            con.execute('INSERT INTO sessions(token_hash,user_id,expires_at) VALUES(?,?,?)', (token_hash(f'tok-{buyer}'),buyer,(datetime.now(timezone.utc)+timedelta(hours=1)).isoformat()))
            for product in (112812,112813):
                con.execute('INSERT INTO saved_cart_items(buyer_id,product_id,quantity) VALUES(?,?,?)', (buyer,product,1))


def checkout(buyer, key):
    payload={'farmer_id':112811,'fulfillment':'dostawa','delivery_city':'Kraków','delivery_street':'Polna 2','delivery_postal_code':'30-001'}
    with TestClient(app) as client:
        return client.post('/cart/checkout-test',json=payload,headers={'Authorization':f'Bearer tok-{buyer}','Idempotency-Key':key})


def test_two_buyers_multiline_atomic_stock_and_single_delivery():
    setup_cart()
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(lambda b:checkout(b,f'checkout-request-{b}'),(112814,112815)))
    assert sorted(r.status_code for r in results)==[201,409],[(r.status_code,r.text) for r in results]
    ok=next(r.json() for r in results if r.status_code==201)
    assert ok['total_grosze']==2250,ok
    assert ok['delivery_grosze']==250,ok
    with db() as con:
        assert con.execute('SELECT stock FROM products WHERE id=112812').fetchone()['stock']==1
        assert con.execute('SELECT stock FROM products WHERE id=112813').fetchone()['stock']==0
        assert con.execute('SELECT COUNT(*) n FROM shipment_groups WHERE farmer_id=112811').fetchone()['n']==1
        assert con.execute('SELECT COUNT(*) n FROM orders WHERE buyer_id IN (112814,112815)').fetchone()['n']==2


    winning_buyer=112814 if results[0].status_code==201 else 112815
    replay=checkout(winning_buyer,f'checkout-request-{winning_buyer}')
    assert replay.status_code==201,replay.text
    assert replay.json()==ok
    with db() as con:
        assert con.execute('SELECT COUNT(*) n FROM shipment_groups WHERE farmer_id=112811').fetchone()['n']==1
        assert con.execute('SELECT COUNT(*) n FROM orders WHERE buyer_id IN (112814,112815)').fetchone()['n']==2

    # Losing buyer cannot turn an out-of-stock checkout into a shipment by retrying.
    losing_buyer = 112815 if winning_buyer == 112814 else 112814
    retry = checkout(losing_buyer, f'new-request-after-stock-exhausted-{losing_buyer}')
    assert retry.status_code == 409, retry.text
    with db() as con:
        assert con.execute('SELECT stock FROM products WHERE id=112812').fetchone()['stock'] == 1
        assert con.execute('SELECT stock FROM products WHERE id=112813').fetchone()['stock'] == 0
        assert con.execute('SELECT COUNT(*) n FROM shipment_groups WHERE farmer_id=112811').fetchone()['n'] == 1
        assert con.execute('SELECT COUNT(*) n FROM orders WHERE buyer_id IN (112814,112815)').fetchone()['n'] == 2

"""Basket and quote share a 50-lines-per-shipment (seller) limit."""
import os
import tempfile
from pathlib import Path
os.environ['WIEJSKAPAKA_DB'] = str(Path(tempfile.mkdtemp()) / 'seller_limits.sqlite3')
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from backend.app import app, db, token_hash


def test_multiple_sellers_can_each_have_50_lines_and_quote_matches():
    client = TestClient(app)
    with db() as con:
        for uid, role in [(8701, 'rolnik'), (8702, 'rolnik'), (8703, 'klient')]:
            con.execute('INSERT INTO users(id,email,password_hash,role) VALUES(?,?,?,?)',
                        (uid, f'{uid}@example.test', 'x', role))
        con.execute('INSERT INTO sessions(token_hash,user_id,expires_at) VALUES(?,?,?)',
                    (token_hash('per-seller-buyer'), 8703,
                     (datetime.now(timezone.utc)+timedelta(hours=1)).isoformat()))
        for i in range(102):
            con.execute('INSERT INTO products(id,farmer_id,name,price_grosze,delivery_grosze,stock) VALUES(?,?,?,?,?,?)',
                        (8800+i, 8701 if i < 51 else 8702, f'Item {i}', 100, 300 if i < 51 else 500, 5))
    headers = {'Authorization': 'Bearer per-seller-buyer'}
    items = []
    for i in list(range(50)) + list(range(51,101)):
        pid = 8800+i
        r = client.put('/cart/items', headers=headers, json={'product_id':pid,'quantity':1})
        assert r.status_code == 200, (i, r.text)
        items.append({'product_id':pid,'quantity':1})
    quote = client.post('/cart/quote', headers=headers,
                        json={'items':items,'fulfillment':'dostawa'})
    assert quote.status_code == 200, quote.text
    data = quote.json()
    assert data['subtotal_grosze'] == 10000
    assert data['delivery_grosze'] == 800
    assert data['total_grosze'] == 10800
    assert [(s['farmer_id'],s['items_count'],s['total_grosze']) for s in data['shipments']] == [
        (8701,50,5300),(8702,50,5500)]
    assert sum(s['total_grosze'] for s in data['shipments']) == data['total_grosze']
    # A 51st line for the first seller must fail in both basket and quote.
    assert client.put('/cart/items', headers=headers, json={'product_id':8850,'quantity':1}).status_code == 422
    over = client.post('/cart/quote', headers=headers,
                       json={'items':items+[{'product_id':8850,'quantity':1}], 'fulfillment':'dostawa'})
    assert over.status_code == 422
    # Updating an existing line remains allowed.
    assert client.put('/cart/items', headers=headers,
                      json={'product_id':8800,'quantity':2}).status_code == 200
    with db() as con:
        assert con.execute('SELECT COUNT(*) AS n FROM saved_cart_items WHERE buyer_id=8703').fetchone()['n'] == 100
        assert con.execute('SELECT stock FROM products WHERE id=8800').fetchone()['stock'] == 5


def test_pickup_quote_is_zero_delivery_per_seller():
    client = TestClient(app)
    with db() as con:
        con.execute('INSERT INTO users(id,email,password_hash,role) VALUES(?,?,?,?)',
                    (8790,'pickup@example.test','x','klient'))
        con.execute('INSERT INTO sessions(token_hash,user_id,expires_at) VALUES(?,?,?)',
                    (token_hash('pickup-buyer'),8790,
                     (datetime.now(timezone.utc)+timedelta(hours=1)).isoformat()))
    r = client.post('/cart/quote', headers={'Authorization':'Bearer pickup-buyer'},
                    json={'items':[{'product_id':8800,'quantity':1}, {'product_id':8851,'quantity':1}],
                          'fulfillment':'odbior'})
    assert r.status_code == 200, r.text
    assert r.json()['delivery_grosze'] == 0
    assert all(s['delivery_grosze'] == 0 for s in r.json()['shipments'])

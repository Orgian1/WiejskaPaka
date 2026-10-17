"""Duplicate checkout protection, with a real SQLite transaction."""
import os
import tempfile
from pathlib import Path
os.environ['WIEJSKAPAKA_DB'] = str(Path(tempfile.mkdtemp()) / 'idempotency.sqlite3')
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from backend.app import app, db, token_hash


def test_checkout_replay_does_not_charge_or_reduce_stock_twice():
    client = TestClient(app)
    with db() as con:
        for uid, role in [(99101, 'rolnik'), (99102, 'klient')]:
            con.execute('INSERT INTO users(id,email,password_hash,role) VALUES(?,?,?,?)',
                        (uid, f'{uid}@example.test', 'x', role))
        con.execute('INSERT INTO sessions(token_hash,user_id,expires_at) VALUES(?,?,?)',
                    (token_hash('buyer-idempotency'), 99102,
                     (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()))
        for pid in (99111,99112):
            con.execute('INSERT INTO products(id,farmer_id,name,price_grosze,delivery_grosze,stock) VALUES(?,?,?,?,?,?)',
                        (pid, 99101, 'Product', 1000, 250, 5))
            con.execute('INSERT INTO saved_cart_items(buyer_id,product_id,quantity) VALUES(?,?,?)',
                        (99102, pid, 1))
    headers={'Authorization':'Bearer buyer-idempotency','Idempotency-Key':'checkout-unique-99102'}
    body={'farmer_id':99101,'fulfillment':'dostawa','delivery_city':'Kraków',
          'delivery_street':'Polna 2','delivery_postal_code':'30-001'}
    first=client.post('/cart/checkout-test',headers=headers,json=body)
    assert first.status_code == 201, first.text
    assert first.json()['total_grosze'] == 2250
    second=client.post('/cart/checkout-test',headers=headers,json=body)
    assert second.status_code == 201, second.text
    assert second.json() == first.json()
    changed=client.post('/cart/checkout-test',headers=headers,json={**body,'delivery_street':'Inna 3'})
    assert changed.status_code == 409
    with db() as con:
        assert con.execute('SELECT COUNT(*) AS n FROM shipment_groups WHERE buyer_id=99102').fetchone()['n'] == 1
        assert con.execute('SELECT COUNT(*) AS n FROM orders WHERE buyer_id=99102').fetchone()['n'] == 2
        assert [r['stock'] for r in con.execute('SELECT stock FROM products WHERE id IN (99111,99112) ORDER BY id')] == [4,4]
        assert con.execute('SELECT COUNT(*) AS n FROM checkout_idempotency WHERE buyer_id=99102').fetchone()['n'] == 1

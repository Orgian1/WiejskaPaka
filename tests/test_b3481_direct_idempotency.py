"""Direct-order idempotency: replay, stock, mismatched payload, user isolation."""
import os
import tempfile
from pathlib import Path
os.environ['WIEJSKAPAKA_DB'] = str(Path(tempfile.mkdtemp()) / 'direct.sqlite3')
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from backend.app import app, db, token_hash


def test_direct_order_replay_and_conflict():
    client = TestClient(app)
    with db() as con:
        for uid, role in [(98001, 'rolnik'), (98002, 'klient'), (98003, 'klient')]:
            con.execute('INSERT INTO users(id,email,password_hash,role) VALUES(?,?,?,?)',
                        (uid, f'{uid}@example.test', 'x', role))
        for uid, token in [(98002, 'direct-buyer-1'), (98003, 'direct-buyer-2')]:
            con.execute('INSERT INTO sessions(token_hash,user_id,expires_at) VALUES(?,?,?)',
                        (token_hash(token), uid, (datetime.now(timezone.utc)+timedelta(hours=1)).isoformat()))
        con.execute('INSERT INTO products(id,farmer_id,name,price_grosze,delivery_grosze,stock) VALUES(?,?,?,?,?,?)',
                    (98011,98001,'Jabłka',1200,350,3))
    body={'product_id':98011,'quantity':1,'fulfillment':'dostawa',
          'delivery_city':'Kraków','delivery_street':'Polna 2','delivery_postal_code':'30-001'}
    headers={'Authorization':'Bearer direct-buyer-1','Idempotency-Key':'direct-unique-98002'}
    first=client.post('/orders',headers=headers,json=body)
    assert first.status_code==201,first.text
    assert first.json()['total_grosze']==1550
    replay=client.post('/orders',headers=headers,json=body)
    assert replay.status_code==201 and replay.json()==first.json()
    conflict=client.post('/orders',headers=headers,json={**body,'quantity':2})
    assert conflict.status_code==409
    other=client.post('/orders',headers={'Authorization':'Bearer direct-buyer-2',
                                       'Idempotency-Key':'direct-unique-98002'},json=body)
    assert other.status_code==201,other.text
    with db() as con:
        assert con.execute('SELECT COUNT(*) AS n FROM orders WHERE buyer_id IN (98002,98003)').fetchone()['n']==2
        assert con.execute('SELECT stock FROM products WHERE id=98011').fetchone()['stock']==1
        assert con.execute("SELECT COUNT(*) AS n FROM checkout_idempotency WHERE request_key LIKE 'direct:%' AND buyer_id IN (98002,98003)").fetchone()['n']==2


def test_invalid_direct_idempotency_key():
    client=TestClient(app)
    response=client.post('/orders',headers={'Authorization':'Bearer direct-buyer-1',
                                           'Idempotency-Key':'short'},json={})
    assert response.status_code in (401,422)

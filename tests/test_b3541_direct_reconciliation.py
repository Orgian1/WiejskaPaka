"""A buyer can reconcile a lost direct-order response without exposing its PIN."""
import os
import tempfile
from pathlib import Path
os.environ['WIEJSKAPAKA_DB'] = str(Path(tempfile.mkdtemp()) / 'reconcile.sqlite3')
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from backend.app import app, db, token_hash


def test_direct_status_scoped_to_buyer_and_without_pin():
    client = TestClient(app)
    with db() as con:
        for uid, role in [(97101, 'rolnik'), (97102, 'klient'), (97103, 'klient')]:
            con.execute('INSERT INTO users(id,email,password_hash,role) VALUES(?,?,?,?)',
                        (uid, f'{uid}@example.test', 'x', role))
        for uid in (97102, 97103):
            con.execute('INSERT INTO sessions(token_hash,user_id,expires_at) VALUES(?,?,?)',
                        (token_hash(f'reconcile-{uid}'), uid,
                         (datetime.now(timezone.utc)+timedelta(hours=1)).isoformat()))
        con.execute('INSERT INTO products(id,farmer_id,name,price_grosze,delivery_grosze,stock) VALUES(?,?,?,?,?,?)',
                    (97111,97101,'Jabłka',500,200,2))
    key='reconcile-key-97102'
    h={'Authorization':'Bearer reconcile-97102'}
    path='/orders/idempotency-status/'+key
    assert client.get(path, headers=h).json()=={'completed':False}
    order=client.post('/orders', headers={**h,'Idempotency-Key':key},
                      json={'product_id':97111,'quantity':1,'fulfillment':'dostawa',
                            'delivery_city':'Kraków','delivery_street':'Polna 2',
                            'delivery_postal_code':'30-001'})
    assert order.status_code==201,order.text
    status=client.get(path,headers=h)
    assert status.status_code==200
    assert status.json()=={'completed':True,'order_id':order.json()['id']}
    assert 'pin' not in status.text.lower()
    assert client.get(path,headers={'Authorization':'Bearer reconcile-97103'}).json()=={'completed':False}
    assert client.get(path).status_code==401
    assert client.get('/orders/idempotency-status/short',headers=h).status_code==422

import os
import tempfile
from pathlib import Path
os.environ['WIEJSKAPAKA_DB'] = str(Path(tempfile.mkdtemp()) / 'reconciliation.sqlite3')
from fastapi.testclient import TestClient
from backend.app import app, db, token_hash
from datetime import datetime, timezone, timedelta


def test_reconciliation_detects_delivery_mismatch_and_protects_access():
    client = TestClient(app)
    with db() as con:
        for uid, role in [(901, 'admin'), (902, 'klient'), (903, 'rolnik')]:
            con.execute('INSERT INTO users(id,email,password_hash,role) VALUES(?,?,?,?)',
                        (uid, f'b901-{uid}@test.pl', 'x', role))
            con.execute('INSERT INTO sessions(token_hash,user_id,expires_at) VALUES(?,?,?)',
                        (token_hash(f'b901-{uid}'), uid,
                         (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()))
        for pid in (901, 902):
            con.execute('INSERT INTO products(id,farmer_id,name,price_grosze,delivery_grosze,stock) VALUES(?,?,?,?,?,?)',
                        (pid, 903, 'Produkt', 1000, 300, 3))
            con.execute('INSERT INTO saved_cart_items(buyer_id,product_id,quantity) VALUES(?,?,?)', (902, pid, 1))
    buyer = {'Authorization': 'Bearer b901-902'}
    admin = {'Authorization': 'Bearer b901-901'}
    checkout = client.post('/cart/checkout-test', headers=buyer,
                           json={'fulfillment':'dostawa', 'delivery_city':'Warszawa',
                                 'delivery_street':'Testowa 1', 'delivery_postal_code':'00-001'})
    assert checkout.status_code == 201, checkout.text
    assert client.get('/admin/shipments/reconciliation', headers=buyer).status_code == 403
    result = client.get('/admin/shipments/reconciliation?only_issues=true', headers=admin)
    assert result.status_code == 200, result.text
    assert all('delivery_mismatch' not in x['issues'] for x in result.json()['shipments'])
    with db() as con:
        con.execute('UPDATE shipment_groups SET delivery_grosze=999')
    result = client.get('/admin/shipments/reconciliation?only_issues=true', headers=admin)
    assert result.status_code == 200, result.text
    assert result.json()['total'] >= 1
    assert 'delivery_mismatch' in result.json()['shipments'][0]['issues']
    assert client.get('/admin/shipments/reconciliation?limit=0', headers=admin).status_code == 422

import os
import tempfile
from pathlib import Path
os.environ['WIEJSKAPAKA_DB'] = str(Path(tempfile.mkdtemp()) / 'admin_shipments.sqlite3')
from fastapi.testclient import TestClient
from backend.app import app, db, token_hash
from datetime import datetime, timezone, timedelta


def test_admin_shipment_overview_and_access_control():
    client = TestClient(app)
    with db() as con:
        for uid, role in [(741, 'admin'), (742, 'klient'), (743, 'rolnik')]:
            con.execute('INSERT INTO users(id,email,password_hash,role) VALUES(?,?,?,?)',
                        (uid, f'b741-{uid}@test.pl', 'x', role))
            con.execute('INSERT INTO sessions(token_hash,user_id,expires_at) VALUES(?,?,?)',
                        (token_hash(f'b741-{uid}'), uid,
                         (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()))
        for pid in (741, 742):
            con.execute('INSERT INTO products(id,farmer_id,name,price_grosze,delivery_grosze,stock) VALUES(?,?,?,?,?,?)',
                        (pid, 743, 'Produkt', 1000, 300, 3))
            con.execute('INSERT INTO saved_cart_items(buyer_id,product_id,quantity) VALUES(?,?,?)', (742, pid, 1))
    buyer = {'Authorization': 'Bearer b741-742'}
    order = client.post('/cart/checkout-test', headers=buyer,
                        json={'fulfillment':'dostawa', 'delivery_city':'Warszawa',
                              'delivery_street':'Testowa 1', 'delivery_postal_code':'00-001'})
    assert order.status_code == 201, order.text
    assert client.get('/admin/shipments/overview', headers=buyer).status_code == 403
    admin = {'Authorization': 'Bearer b741-741'}
    r = client.get('/admin/shipments/overview', headers=admin)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data['total'] == 1
    shipment = data['shipments'][0]
    assert shipment['order_count'] == 2
    assert shipment['delivery_grosze'] == 300
    assert shipment['products_grosze'] == 2000
    assert shipment['total_grosze'] == 2300
    assert shipment['refund_test_grosze'] == 0
    assert 'delivery_street' not in str(data)
    assert 'pin' not in str(data).lower()
    assert client.get('/admin/shipments/overview?limit=0', headers=admin).status_code == 422
    assert client.get('/admin/shipments/overview?status=invalid', headers=admin).status_code == 422
    filtered = client.get('/admin/shipments/overview?status=odebrane', headers=admin).json()
    assert filtered['total'] == 0


def test_admin_shipment_audit_privacy_and_ledger():
    client = TestClient(app)
    admin = {'Authorization': 'Bearer b741-741'}
    buyer = {'Authorization': 'Bearer b741-742'}
    overview = client.get('/admin/shipments/overview', headers=admin)
    assert overview.status_code == 200
    if not overview.json()['shipments']:
        test_admin_shipment_overview_and_access_control()
        overview = client.get('/admin/shipments/overview', headers=admin)
    shipment_id = overview.json()['shipments'][0]['shipment_id']
    assert client.get(f'/admin/shipments/{shipment_id}/audit', headers=buyer).status_code == 403
    result = client.get(f'/admin/shipments/{shipment_id}/audit', headers=admin)
    assert result.status_code == 200, result.text
    data = result.json()
    assert data['delivery_consistent'] is True
    assert data['refund_test_grosze'] == 0
    assert data['total_grosze'] == sum(x['total_grosze'] for x in data['items'])
    assert all('events' in x for x in data['items'])
    assert not any(key in str(data).lower() for key in ('password_hash', 'pin_hash', 'delivery_street'))
    assert client.get('/admin/shipments/nie-ma/audit', headers=admin).status_code == 404

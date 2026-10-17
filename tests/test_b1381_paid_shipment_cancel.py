import os
import tempfile
from pathlib import Path
os.environ['WIEJSKAPAKA_DB'] = str(Path(tempfile.mkdtemp()) / 'paid_refund.sqlite3')
os.environ['WP_ENABLE_TEST_PAYMENTS'] = '1'
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from backend.app import app, db, token_hash


def test_paid_shipment_refund_once_and_restore_stock_once():
    client = TestClient(app)
    with db() as con:
        for uid, role in [(1381, 'rolnik'), (1382, 'klient')]:
            con.execute('INSERT INTO users(id,email,password_hash,role) VALUES(?,?,?,?)',
                        (uid, f'b1381-{uid}@example.org', 'x', role))
            con.execute('INSERT INTO sessions(token_hash,user_id,expires_at) VALUES(?,?,?)',
                        (token_hash(f'b1381-{uid}'),uid,(datetime.now(timezone.utc)+timedelta(hours=1)).isoformat()))
        for pid in (1381, 1382):
            con.execute('INSERT INTO products(id,farmer_id,name,price_grosze,delivery_grosze,stock) VALUES(?,?,?,?,?,?)',
                        (pid,1381,'Produkt',1000,300,5))
            con.execute('INSERT INTO saved_cart_items(buyer_id,product_id,quantity) VALUES(?,?,?)',(1382,pid,1))
    headers={'Authorization':'Bearer b1381-1382'}
    checkout=client.post('/cart/checkout-test',headers=headers,json={'fulfillment':'dostawa','delivery_city':'Warszawa','delivery_street':'Testowa 1','delivery_postal_code':'00-001'})
    assert checkout.status_code==201, checkout.text
    data=checkout.json()
    assert data['total_grosze']==2300
    for order in data['orders']:
        response=client.post(f'/test/payments/{order["id"]}/events',headers=headers,json={'event_id':f'paid-{order["id"]}', 'event_type':'payment_success_test'})
        assert response.status_code==200,response.text
    url=f'/shipments/{data["shipment_id"]}/cancel-paid-test'
    first=client.post(url,headers=headers)
    assert first.status_code==200,first.text
    assert first.json()['refund_grosze']==2300
    assert first.json()['already_processed'] is False
    again=client.post(url,headers=headers)
    assert again.status_code==200,again.text
    assert again.json()['refund_grosze']==2300
    assert again.json()['already_processed'] is True
    with db() as con:
        assert [r['stock'] for r in con.execute('SELECT stock FROM products WHERE id IN (1381,1382) ORDER BY id')]==[5,5]
        assert con.execute("SELECT COUNT(*) AS n FROM payment_simulation_events WHERE event_type='customer_cancel_refund_test'").fetchone()['n']==2
        assert con.execute("SELECT COUNT(*) AS n FROM orders WHERE status='anulowane_testowo'").fetchone()['n']==2

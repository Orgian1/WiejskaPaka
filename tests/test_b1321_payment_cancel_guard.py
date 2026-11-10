import os
import tempfile
from pathlib import Path
os.environ['WIEJSKAPAKA_DB'] = str(Path(tempfile.mkdtemp()) / 'paid_cancel.sqlite3')
os.environ['WP_ENABLE_TEST_PAYMENTS'] = '1'
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from backend.app import app, db, token_hash


def test_paid_shipment_cannot_be_cancelled_or_paid_after_cancel():
    client = TestClient(app)
    with db() as con:
        for uid, role in [(1321, 'rolnik'), (1322, 'klient')]:
            con.execute('INSERT INTO users(id,email,password_hash,role) VALUES(?,?,?,?)',
                        (uid, f'b1321-{uid}@example.org', 'x', role))
            con.execute('INSERT INTO sessions(token_hash,user_id,expires_at) VALUES(?,?,?)',
                        (token_hash(f'b1321-{uid}'),uid,(datetime.now(timezone.utc)+timedelta(hours=1)).isoformat()))
        for pid in (1321,1322):
            con.execute('INSERT INTO products(id,farmer_id,name,price_grosze,delivery_grosze,stock) VALUES(?,?,?,?,?,?)',
                        (pid,1321,'Produkt',1000,200,5))
            con.execute('INSERT INTO saved_cart_items(buyer_id,product_id,quantity) VALUES(?,?,?)',(1322,pid,1))
    headers={'Authorization':'Bearer b1321-1322'}
    def checkout():
        response=client.post('/cart/checkout-test',headers=headers,json={'fulfillment':'dostawa','delivery_city':'Warszawa','delivery_street':'Testowa 1','delivery_postal_code':'00-001'})
        assert response.status_code==201,response.text
        return response.json()
    first=checkout()
    order=first['orders'][0]['id']
    paid=client.post(f'/test/payments/{order}/events',headers=headers,json={'event_id':'paid-1321','event_type':'payment_success_test'})
    assert paid.status_code==200,paid.text
    denied=client.post(f'/shipments/{first["shipment_id"]}/cancel-test',headers=headers)
    assert denied.status_code==409,denied.text
    with db() as con:
        assert con.execute('SELECT COUNT(*) AS n FROM orders WHERE status=?',('anulowane_testowo',)).fetchone()['n']==0
        assert [r['stock'] for r in con.execute('SELECT stock FROM products WHERE id IN (1321,1322) ORDER BY id')]==[4,4]
    # Separate unpaid order can be cancelled, but cannot later be paid.
    with db() as con:
        con.execute('INSERT INTO saved_cart_items(buyer_id,product_id,quantity) VALUES(?,?,?)',(1322,1321,1))
    second=checkout()
    assert client.post(f'/shipments/{second["shipment_id"]}/cancel-test',headers=headers).status_code==200
    cancelled_id=second['orders'][0]['id']
    late=client.post(f'/test/payments/{cancelled_id}/events',headers=headers,json={'event_id':'late-1321','event_type':'payment_success_test'})
    assert late.status_code==409,late.text

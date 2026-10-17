import os
import tempfile
from pathlib import Path
os.environ['WIEJSKAPAKA_DB'] = str(Path(tempfile.mkdtemp()) / 'failure.sqlite3')
os.environ['WP_ENABLE_TEST_PAYMENTS'] = '1'
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from backend.app import app, db, token_hash


def test_full_shipment_refund_and_idempotency():
    client = TestClient(app)
    with db() as con:
        for uid, role in [(641, 'rolnik'), (642, 'klient'), (643, 'dostawca')]:
            con.execute('INSERT INTO users(id,email,password_hash,role) VALUES(?,?,?,?)',
                        (uid, f'b641-{uid}@example.org', 'x', role))
            con.execute('INSERT INTO sessions(token_hash,user_id,expires_at) VALUES(?,?,?)',
                        (token_hash(f'b641-{uid}'),uid,(datetime.now(timezone.utc)+timedelta(hours=1)).isoformat()))
        for pid in (641,642):
            con.execute('INSERT INTO products(id,farmer_id,name,price_grosze,delivery_grosze,stock) VALUES(?,?,?,?,?,?)',
                        (pid,641,'Towar',1000,250,5))
            con.execute('INSERT INTO saved_cart_items(buyer_id,product_id,quantity) VALUES(?,?,?)',(642,pid,1))
    h=lambda uid:{'Authorization':f'Bearer b641-{uid}'}
    checkout=client.post('/cart/checkout-test',headers=h(642),json={'fulfillment':'dostawa','delivery_city':'Warszawa','delivery_street':'Testowa 1','delivery_postal_code':'00-001'})
    assert checkout.status_code==201,checkout.text
    shipment=checkout.json()['shipment_id']
    assert checkout.json()['total_grosze']==2250
    order_ids=[o['id'] for o in checkout.json()['orders']]
    for order_id in order_ids:
        paid=client.post(f'/test/payments/{order_id}/events',headers=h(642),json={'event_id':f'paid-{order_id}','event_type':'payment_success_test'})
        assert paid.status_code==200,paid.text
    assert client.post(f'/shipments/{shipment}/assign-courier-test',headers=h(641),json={'courier_id':643}).status_code==200
    assert client.post(f'/shipments/{shipment}/dispatch-test',headers=h(641)).status_code==200
    url=f'/shipments/{shipment}/courier-failure-test'
    assert client.post(url,headers=h(642),json={'reason':'dostawca_nie_przyjechal'}).status_code==403
    result=client.post(url,headers=h(641),json={'reason':'dostawca_nie_przyjechal'})
    assert result.status_code==200,result.text
    assert result.json()['refund_grosze']==2250
    assert result.json()['already_processed'] is False
    retry=client.post(url,headers=h(641),json={'reason':'dostawca_nie_przyjechal'})
    assert retry.status_code==200 and retry.json()['already_processed'] is True
    assert retry.json()['refund_grosze']==2250
    with db() as con:
        assert con.execute("SELECT COUNT(*) AS n FROM orders WHERE status='nieudana_dostawa_testowo'").fetchone()['n']==2
        assert con.execute('SELECT SUM(refund_grosze) AS n FROM payment_simulations').fetchone()['n']==2250
    assert client.post(f'/shipments/{shipment}/confirm',headers=h(643),json={'pin':checkout.json()['shipment_pin_test_only'],'checked_goods':True}).status_code==409

"""Cross-seller checkout: delivery charged per shipment, never per item."""
import os
import tempfile
from pathlib import Path
os.environ['WIEJSKAPAKA_DB'] = str(Path(tempfile.mkdtemp()) / 'shipments.sqlite3')
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from backend.app import app, db, token_hash


def test_two_farmers_two_separate_shipments_one_fee_each():
    client = TestClient(app)
    with db() as con:
        for uid, role in [(9101, 'rolnik'), (9102, 'rolnik'), (9103, 'klient')]:
            con.execute('INSERT INTO users(id,email,password_hash,role) VALUES(?,?,?,?)',
                        (uid, f'{uid}@example.test', 'x', role))
        con.execute('INSERT INTO sessions(token_hash,user_id,expires_at) VALUES(?,?,?)',
                    (token_hash('buyer-shipment-regression'), 9103,
                     (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()))
        for pid, farmer, price, delivery in [(9111,9101,1000,150), (9112,9101,2000,250),
                                             (9121,9102,3000,400), (9122,9102,500,100)]:
            con.execute('INSERT INTO products(id,farmer_id,name,price_grosze,delivery_grosze,stock) VALUES(?,?,?,?,?,?)',
                        (pid, farmer, f'Product {pid}', price, delivery, 10))
            con.execute('INSERT INTO saved_cart_items(buyer_id,product_id,quantity) VALUES(?,?,?)',
                        (9103, pid, 1))
    headers = {'Authorization':'Bearer buyer-shipment-regression'}
    def checkout(farmer):
        return client.post('/cart/checkout-test', headers=headers, json={
            'farmer_id':farmer,'fulfillment':'dostawa','delivery_city':'Kraków',
            'delivery_street':'Polna 2','delivery_postal_code':'30-001'})
    first = checkout(9101)
    assert first.status_code == 201, first.text
    assert first.json()['delivery_grosze'] == 250
    assert first.json()['total_grosze'] == 3250
    with db() as con:
        assert [r['product_id'] for r in con.execute('SELECT product_id FROM saved_cart_items WHERE buyer_id=9103 ORDER BY product_id')] == [9121,9122]
    second = checkout(9102)
    assert second.status_code == 201, second.text
    assert second.json()['delivery_grosze'] == 400
    assert second.json()['total_grosze'] == 3900
    assert first.json()['shipment_id'] != second.json()['shipment_id']
    with db() as con:
        for shipment_id, fee in [(first.json()['shipment_id'],250), (second.json()['shipment_id'],400)]:
            rows = con.execute('SELECT o.delivery_grosze FROM orders o JOIN shipment_order_links l ON l.order_id=o.id WHERE l.shipment_id=?', (shipment_id,)).fetchall()
            assert len(rows) == 2
            assert sum(row['delivery_grosze'] for row in rows) == fee
        assert con.execute('SELECT COUNT(*) AS n FROM saved_cart_items WHERE buyer_id=9103').fetchone()['n'] == 0


def test_checkout_limit_applies_only_to_selected_farmer():
    client = TestClient(app)
    with db() as con:
        for uid, role in [(9201,'rolnik'),(9202,'rolnik'),(9203,'klient')]:
            con.execute('INSERT INTO users(id,email,password_hash,role) VALUES(?,?,?,?)',
                        (uid,f'{uid}@example.test','x',role))
        con.execute('INSERT INTO sessions(token_hash,user_id,expires_at) VALUES(?,?,?)',
                    (token_hash('large-multiseller-buyer'),9203,
                     (datetime.now(timezone.utc)+timedelta(hours=1)).isoformat()))
        for i in range(51):
            con.execute('INSERT INTO products(id,farmer_id,name,price_grosze,delivery_grosze,stock) VALUES(?,?,?,?,?,?)',
                        (9300+i,9202,f'Other {i}',100,0,2))
            con.execute('INSERT INTO saved_cart_items(buyer_id,product_id,quantity) VALUES(?,?,?)', (9203,9300+i,1))
        con.execute('INSERT INTO products(id,farmer_id,name,price_grosze,delivery_grosze,stock) VALUES(?,?,?,?,?,?)',
                    (9400,9201,'Selected',1000,200,2))
        con.execute('INSERT INTO saved_cart_items(buyer_id,product_id,quantity) VALUES(?,?,?)', (9203,9400,1))
    result=client.post('/cart/checkout-test',headers={'Authorization':'Bearer large-multiseller-buyer'},json={
        'farmer_id':9201,'fulfillment':'dostawa','delivery_city':'Kraków',
        'delivery_street':'Polna 2','delivery_postal_code':'30-001'})
    assert result.status_code==201,result.text
    assert result.json()['total_grosze']==1200
    with db() as con:
        assert con.execute('SELECT COUNT(*) AS n FROM saved_cart_items WHERE buyer_id=9203').fetchone()['n']==51

import os
import tempfile
from pathlib import Path
os.environ['WIEJSKAPAKA_DB'] = str(Path(tempfile.mkdtemp()) / 'shared_delivery.sqlite3')
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from backend.app import app, db, token_hash


def test_shared_delivery_once_for_multiple_lines():
    c = TestClient(app)
    with db() as con:
        con.execute("INSERT INTO users(id,email,password_hash,role) VALUES(901,'farmer901@test.pl','x','rolnik')")
        con.execute("INSERT INTO users(id,email,password_hash,role) VALUES(902,'buyer902@test.pl','x','klient')")
        con.execute('INSERT INTO sessions(token_hash,user_id,expires_at) VALUES(?,?,?)',
                    (token_hash('sharedbuyer'), 902, (datetime.now(timezone.utc)+timedelta(hours=1)).isoformat()))
        for product_id, fee in ((910, 150), (911, 300)):
            con.execute('INSERT INTO products(id,farmer_id,name,price_grosze,delivery_grosze,stock) VALUES(?,?,?,?,?,?)',
                        (product_id, 901, 'Warzywa', 1000, fee, 5))
            con.execute('INSERT INTO saved_cart_items(buyer_id,product_id,quantity) VALUES(?,?,?)',
                        (902, product_id, 1))
    result = c.post('/cart/checkout-test', headers={'Authorization':'Bearer sharedbuyer'}, json={
        'farmer_id':901, 'fulfillment':'dostawa', 'delivery_city':'Kraków',
        'delivery_street':'Polna 1', 'delivery_postal_code':'30-001'})
    assert result.status_code == 201, result.text
    assert result.json()['total_grosze'] == 2300
    assert result.json()['delivery_grosze'] == 300
    with db() as con:
        orders = con.execute('SELECT delivery_grosze,total_grosze FROM orders WHERE buyer_id=902 ORDER BY id').fetchall()
        assert [r['delivery_grosze'] for r in orders] == [300, 0]
        assert sum(r['total_grosze'] for r in orders) == 2300

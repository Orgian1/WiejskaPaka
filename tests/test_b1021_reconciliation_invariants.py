import os
import tempfile
from pathlib import Path
os.environ['WIEJSKAPAKA_DB'] = str(Path(tempfile.mkdtemp()) / 'invariants.sqlite3')
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from backend.app import app, db, token_hash


def test_reconciliation_detects_wrong_owner_and_double_delivery():
    client = TestClient(app)
    with db() as con:
        for uid, role in [(1021, 'admin'), (1022, 'klient'), (1023, 'rolnik'), (1024, 'rolnik')]:
            con.execute('INSERT INTO users(id,email,password_hash,role) VALUES(?,?,?,?)',
                        (uid, f'b1021-{uid}@test.pl', 'x', role))
        con.execute('INSERT INTO sessions(token_hash,user_id,expires_at) VALUES(?,?,?)',
                    (token_hash('b1021-admin'), 1021, (datetime.now(timezone.utc)+timedelta(hours=1)).isoformat()))
        con.execute("INSERT INTO shipment_groups(id,buyer_id,farmer_id,fulfillment,delivery_grosze,created_at) VALUES('s1021',1022,1023,'dostawa',600,'2026-10-15')")
        for oid in (1021, 1022):
            con.execute('INSERT INTO products(id,farmer_id,name,price_grosze,delivery_grosze,stock) VALUES(?,?,?,?,?,?)',
                        (oid, 1023, 'Test', 1000, 300, 5))
            con.execute('''INSERT INTO orders(id,buyer_id,farmer_id,product_id,quantity,subtotal_grosze,delivery_grosze,total_grosze,fulfillment,status,pickup_code,pin_hash,created_at)
                           VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                        (oid,1022,1024 if oid==1022 else 1023,oid,1,1000,300,1300,'dostawa','nowe',f'pin-{oid}','x','2026-10-15'))
            con.execute('INSERT INTO shipment_order_links(order_id,shipment_id) VALUES(?,?)', (oid,'s1021'))
    response=client.get('/admin/shipments/reconciliation?only_issues=true',headers={'Authorization':'Bearer b1021-admin'})
    assert response.status_code == 200, response.text
    issues=response.json()['shipments'][0]['issues']
    assert 'farmer_mismatch' in issues
    assert 'delivery_charged_multiple_times' in issues
    assert 'buyer_mismatch' not in issues

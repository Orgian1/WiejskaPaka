import os
import tempfile
from pathlib import Path
os.environ['WIEJSKAPAKA_DB'] = str(Path(tempfile.mkdtemp()) / 'line_integrity.sqlite3')
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from backend.app import app, db, token_hash


def test_line_mismatch_even_when_shipment_sum_is_correct():
    client = TestClient(app)
    with db() as con:
        for uid, role in [(1081, 'admin'), (1082, 'klient'), (1083, 'rolnik')]:
            con.execute('INSERT INTO users(id,email,password_hash,role) VALUES(?,?,?,?)',
                        (uid, f'line-{uid}@test.pl', 'x', role))
        con.execute('INSERT INTO sessions(token_hash,user_id,expires_at) VALUES(?,?,?)',
                    (token_hash('line-admin'), 1081,
                     (datetime.now(timezone.utc)+timedelta(hours=1)).isoformat()))
        con.execute("INSERT INTO shipment_groups(id,buyer_id,farmer_id,fulfillment,delivery_grosze,created_at) VALUES('line1081',1082,1083,'dostawa',200,'2026-10-15')")
        for pid in (1081,1082):
            con.execute('INSERT INTO products(id,farmer_id,name,price_grosze,delivery_grosze,stock) VALUES(?,?,?,?,?,?)',
                        (pid,1083,'Test',1000,200,5))
        for oid, subtotal, delivery, total in [(1081,1000,200,1300),(1082,1000,0,900)]:
            con.execute('''INSERT INTO orders(id,buyer_id,farmer_id,product_id,quantity,subtotal_grosze,delivery_grosze,total_grosze,fulfillment,status,pickup_code,pin_hash,created_at)
                           VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                        (oid,1082,1083,oid,1,subtotal,delivery,total,'dostawa','nowe',f'pin-{oid}','x','2026-10-15'))
            con.execute('INSERT INTO shipment_order_links(order_id,shipment_id) VALUES(?,?)',(oid,'line1081'))
    response = client.get('/admin/shipments/reconciliation?only_issues=true',
                          headers={'Authorization':'Bearer line-admin'})
    assert response.status_code == 200, response.text
    item = next(x for x in response.json()['shipments'] if x['shipment_id']=='line1081')
    assert 'order_line_total_mismatch' in item['issues']
    assert 'total_mismatch' not in item['issues']

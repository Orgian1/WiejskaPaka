from tests.authorization_helpers import authorization_for
import pytest
from fastapi import HTTPException
from backend.app import (db, request_invoice_correction, CorrectionRequestIn,
                         my_correction_requests, my_accounting_audit)
from backend.pg_adapter import translate_sql


def test_correction_requests_are_private_and_audited():
    with db() as con:
        con.execute("INSERT INTO users(id,email,password_hash,role) VALUES(930001,'farmer13@test.local','x','rolnik') ON CONFLICT DO NOTHING")
        con.execute("INSERT INTO users(id,email,password_hash,role) VALUES(930002,'buyer13@test.local','x','klient') ON CONFLICT DO NOTHING")
        con.execute("INSERT INTO products(id,farmer_id,name,price_grosze,delivery_grosze,stock) VALUES(930001,930001,'Test',1000,0,1) ON CONFLICT DO NOTHING")
        con.execute("""INSERT INTO orders(id,buyer_id,farmer_id,product_id,quantity,subtotal_grosze,delivery_grosze,total_grosze,fulfillment,status,pickup_code,pin_hash,created_at)
          VALUES(930001,930002,930001,930001,1,1000,0,1000,'odbior','new','T13-930001','hash','2026-01-01') ON CONFLICT DO NOTHING""")
        con.execute("INSERT INTO commission_drafts(id,order_id,farmer_id,basis_grosze,rate_basis_points,commission_grosze,created_at) VALUES(930001,930001,930001,1000,500,50,'2026-01-01') ON CONFLICT DO NOTHING")
        con.execute("""INSERT INTO invoice_drafts(id,commission_draft_id,farmer_id,seller_name,seller_nip,buyer_name,description,net_grosze,created_at)
          VALUES(930001,930001,930001,'Platforma','1234567890','Rolnik','Test',50,'2026-01-01') ON CONFLICT DO NOTHING""")
    with db() as con:
        con.execute("INSERT INTO users(id,email,password_hash,role) VALUES(930003,'farmer13other@test.local','x','rolnik') ON CONFLICT DO NOTHING")
    seller={'id':930001,'role':'rolnik'}
    other={'id':930003,'role':'rolnik'}
    payload=CorrectionRequestIn(invoice_draft_id=930001,reason='Błędna wartość prowizji',requested_net_grosze=40)
    result=request_invoice_correction(payload,user=seller,authorization=authorization_for(seller))
    assert result['status']=='pending_review' and not result['issued']
    assert any(row['id']==result['id'] for row in my_correction_requests(user=seller)['items'])
    assert any(row['correction_request_id']==result['id'] for row in my_accounting_audit(user=seller)['items'])
    assert my_correction_requests(user=other)['items']==[]
    assert my_accounting_audit(user=other)['items']==[]
    with pytest.raises(HTTPException) as exc:
        request_invoice_correction(payload,user=other,authorization=authorization_for(other))
    assert exc.value.status_code==404


def test_pg_insert_returning_for_accounting_tables():
    for table in ('commission_drafts','invoice_drafts','invoice_correction_requests','accounting_audit_events'):
        assert translate_sql(f'INSERT INTO {table}(created_at) VALUES(?)').endswith('RETURNING id')

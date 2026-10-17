import pytest
from fastapi import HTTPException
from backend.app import (db, prepare_accounting_export, validate_accounting_export,
                         acknowledge_accounting_validation, accounting_review_status)


def test_acknowledgement_private_idempotent_and_stays_blocked():
    with db() as con:
        con.execute("INSERT INTO users(id,email,password_hash,role) VALUES(970001,'farmer17@test.local','x','rolnik') ON CONFLICT DO NOTHING")
        con.execute("INSERT INTO users(id,email,password_hash,role) VALUES(970002,'other17@test.local','x','rolnik') ON CONFLICT DO NOTHING")
        con.execute("INSERT INTO users(id,email,password_hash,role) VALUES(970003,'buyer17@test.local','x','klient') ON CONFLICT DO NOTHING")
        con.execute("INSERT INTO products(id,farmer_id,name,price_grosze,delivery_grosze,stock) VALUES(970001,970001,'Test',1000,0,1) ON CONFLICT DO NOTHING")
        con.execute("""INSERT INTO orders(id,buyer_id,farmer_id,product_id,quantity,subtotal_grosze,delivery_grosze,total_grosze,fulfillment,status,pickup_code,pin_hash,created_at)
          VALUES(970001,970003,970001,970001,1,1000,0,1000,'odbior','new','T17-970001','hash','2026-01-01') ON CONFLICT DO NOTHING""")
        con.execute("INSERT INTO commission_drafts(id,order_id,farmer_id,basis_grosze,rate_basis_points,commission_grosze,created_at) VALUES(970001,970001,970001,1000,500,50,'2026-01-01') ON CONFLICT DO NOTHING")
        con.execute("""INSERT INTO invoice_drafts(id,commission_draft_id,farmer_id,seller_name,seller_nip,buyer_name,description,net_grosze,created_at)
          VALUES(970001,970001,970001,'Platforma','1234567890','Rolnik','Test',50,'2026-01-01') ON CONFLICT DO NOTHING""")
    farmer={'id':970001,'role':'rolnik'}
    other={'id':970002,'role':'rolnik'}
    job=prepare_accounting_export(970001,user=farmer)
    assert accounting_review_status(job['id'],user=farmer)['latest_validation_id'] is None
    with pytest.raises(HTTPException) as exc:
        acknowledge_accounting_validation(job['id'],user=farmer)
    assert exc.value.status_code==409
    validate_accounting_export(job['id'],user=farmer)
    assert accounting_review_status(job['id'],user=farmer)['latest_validation_acknowledged'] is False
    a=acknowledge_accounting_validation(job['id'],user=farmer)
    b=acknowledge_accounting_validation(job['id'],user=farmer)
    assert a['id']==b['id'] and not a['tax_approved'] and not a['sent']
    assert accounting_review_status(job['id'],user=farmer)['latest_validation_acknowledged'] is True
    for fn in (accounting_review_status, acknowledge_accounting_validation):
        with pytest.raises(HTTPException) as exc:
            fn(job['id'],user=other)
        assert exc.value.status_code==404
    with db() as con:
        con.execute('UPDATE accounting_export_jobs SET payload_sha256=? WHERE id=?',('0'*64,job['id']))
    validate_accounting_export(job['id'],user=farmer)
    state=accounting_review_status(job['id'],user=farmer)
    assert state['latest_validation_acknowledged'] is False
    assert state['status']=='blocked_tax_review' and not state['ready_for_external_api']

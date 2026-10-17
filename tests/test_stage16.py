import pytest
from fastapi import HTTPException
from backend.app import db, prepare_accounting_export, validate_accounting_export, accounting_validation_history


def test_validation_history_is_private_idempotent_and_changes_are_recorded():
    with db() as con:
        con.execute("INSERT INTO users(id,email,password_hash,role) VALUES(960001,'farmer16@test.local','x','rolnik') ON CONFLICT DO NOTHING")
        con.execute("INSERT INTO users(id,email,password_hash,role) VALUES(960002,'other16@test.local','x','rolnik') ON CONFLICT DO NOTHING")
        con.execute("INSERT INTO users(id,email,password_hash,role) VALUES(960003,'buyer16@test.local','x','klient') ON CONFLICT DO NOTHING")
        con.execute("INSERT INTO products(id,farmer_id,name,price_grosze,delivery_grosze,stock) VALUES(960001,960001,'Test',1000,0,1) ON CONFLICT DO NOTHING")
        con.execute("""INSERT INTO orders(id,buyer_id,farmer_id,product_id,quantity,subtotal_grosze,delivery_grosze,total_grosze,fulfillment,status,pickup_code,pin_hash,created_at)
          VALUES(960001,960003,960001,960001,1,1000,0,1000,'odbior','new','T16-960001','hash','2026-01-01') ON CONFLICT DO NOTHING""")
        con.execute("INSERT INTO commission_drafts(id,order_id,farmer_id,basis_grosze,rate_basis_points,commission_grosze,created_at) VALUES(960001,960001,960001,1000,500,50,'2026-01-01') ON CONFLICT DO NOTHING")
        con.execute("""INSERT INTO invoice_drafts(id,commission_draft_id,farmer_id,seller_name,seller_nip,buyer_name,description,net_grosze,created_at)
          VALUES(960001,960001,960001,'Platforma','1234567890','Rolnik','Test',50,'2026-01-01') ON CONFLICT DO NOTHING""")
    farmer={'id':960001,'role':'rolnik'}
    stranger={'id':960002,'role':'rolnik'}
    job=prepare_accounting_export(960001,user=farmer)
    a=validate_accounting_export(job['id'],user=farmer)
    b=validate_accounting_export(job['id'],user=farmer)
    assert a['validation_id']==b['validation_id']
    assert a['ready_for_external_api'] is False and not a['sent']
    assert len(accounting_validation_history(job['id'],user=farmer)['items'])==1
    with pytest.raises(HTTPException) as e:
        accounting_validation_history(job['id'],user=stranger)
    assert e.value.status_code==404
    with pytest.raises(HTTPException) as e:
        validate_accounting_export(job['id'],user=stranger)
    assert e.value.status_code==404
    with db() as con:
        con.execute('UPDATE accounting_export_jobs SET payload_sha256=? WHERE id=?',('0'*64,job['id']))
    c=validate_accounting_export(job['id'],user=farmer)
    assert c['validation_id']!=a['validation_id']
    assert 'snapshot_changed' in c['issues']
    assert len(accounting_validation_history(job['id'],user=farmer)['items'])==2

import pytest
from fastapi import HTTPException
from backend.app import db, prepare_accounting_export, accounting_export_diagnostics


def test_diagnostics_private_and_blocked():
    # Fixtures from stage 14 are re-created independently for a clean database.
    with db() as con:
        con.execute("INSERT INTO users(id,email,password_hash,role) VALUES(950001,'farmer15@test.local','x','rolnik') ON CONFLICT DO NOTHING")
        con.execute("INSERT INTO users(id,email,password_hash,role) VALUES(950002,'other15@test.local','x','rolnik') ON CONFLICT DO NOTHING")
        con.execute("INSERT INTO users(id,email,password_hash,role) VALUES(950003,'buyer15@test.local','x','klient') ON CONFLICT DO NOTHING")
        con.execute("INSERT INTO products(id,farmer_id,name,price_grosze,delivery_grosze,stock) VALUES(950001,950001,'Test',1000,0,1) ON CONFLICT DO NOTHING")
        con.execute("""INSERT INTO orders(id,buyer_id,farmer_id,product_id,quantity,subtotal_grosze,delivery_grosze,total_grosze,fulfillment,status,pickup_code,pin_hash,created_at)
          VALUES(950001,950003,950001,950001,1,1000,0,1000,'odbior','new','T15-950001','hash','2026-01-01') ON CONFLICT DO NOTHING""")
        con.execute("INSERT INTO commission_drafts(id,order_id,farmer_id,basis_grosze,rate_basis_points,commission_grosze,created_at) VALUES(950001,950001,950001,1000,500,50,'2026-01-01') ON CONFLICT DO NOTHING")
        con.execute("""INSERT INTO invoice_drafts(id,commission_draft_id,farmer_id,seller_name,seller_nip,buyer_name,description,net_grosze,created_at)
          VALUES(950001,950001,950001,'Platforma','1234567890','Rolnik','Test',50,'2026-01-01') ON CONFLICT DO NOTHING""")
    farmer={'id':950001,'role':'rolnik'}
    job=prepare_accounting_export(950001,user=farmer)
    report=accounting_export_diagnostics(job['id'],user=farmer)
    assert report['snapshot_integrity_ok'] is True
    assert report['issues']==['tax_amounts_unverified','tax_review_required']
    assert report['ready_for_external_api'] is False
    assert 'seller_nip' not in report
    with pytest.raises(HTTPException) as err:
        accounting_export_diagnostics(job['id'],user={'id':950002,'role':'rolnik'})
    assert err.value.status_code==404
    with db() as con:
        con.execute("UPDATE accounting_export_jobs SET payload_sha256=? WHERE id=?",('0'*64,job['id']))
    report=accounting_export_diagnostics(job['id'],user=farmer)
    assert report['snapshot_integrity_ok'] is False
    assert 'snapshot_changed' in report['issues']

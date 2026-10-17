import pytest
from fastapi import HTTPException
from backend.app import db, accounting_export_preview, prepare_accounting_export, my_accounting_export_jobs
from backend.pg_adapter import translate_sql


def test_export_jobs_private_idempotent_and_blocked():
    with db() as con:
        con.execute("INSERT INTO users(id,email,password_hash,role) VALUES(940001,'farmer14@test.local','x','rolnik') ON CONFLICT DO NOTHING")
        con.execute("INSERT INTO users(id,email,password_hash,role) VALUES(940002,'farmer14other@test.local','x','rolnik') ON CONFLICT DO NOTHING")
        con.execute("INSERT INTO users(id,email,password_hash,role) VALUES(940003,'buyer14@test.local','x','klient') ON CONFLICT DO NOTHING")
        con.execute("INSERT INTO products(id,farmer_id,name,price_grosze,delivery_grosze,stock) VALUES(940001,940001,'Test',1000,0,1) ON CONFLICT DO NOTHING")
        con.execute("""INSERT INTO orders(id,buyer_id,farmer_id,product_id,quantity,subtotal_grosze,delivery_grosze,total_grosze,fulfillment,status,pickup_code,pin_hash,created_at)
          VALUES(940001,940003,940001,940001,1,1000,0,1000,'odbior','new','T14-940001','hash','2026-01-01') ON CONFLICT DO NOTHING""")
        con.execute("INSERT INTO commission_drafts(id,order_id,farmer_id,basis_grosze,rate_basis_points,commission_grosze,created_at) VALUES(940001,940001,940001,1000,500,50,'2026-01-01') ON CONFLICT DO NOTHING")
        con.execute("""INSERT INTO invoice_drafts(id,commission_draft_id,farmer_id,seller_name,seller_nip,buyer_name,description,net_grosze,created_at)
          VALUES(940001,940001,940001,'Platforma','1234567890','Rolnik','Test',50,'2026-01-01') ON CONFLICT DO NOTHING""")
    farmer={'id':940001,'role':'rolnik'}
    stranger={'id':940002,'role':'rolnik'}
    preview=accounting_export_preview(940001,user=farmer)
    assert preview['net_grosze']==50 and preview['tax_review_required']
    assert 'seller_nip' not in preview and 'buyer_name' not in preview
    first=prepare_accounting_export(940001,user=farmer)
    second=prepare_accounting_export(940001,user=farmer)
    assert first['id']==second['id'] and first['status']=='blocked_tax_review'
    assert not first['sent'] and not first['issued']
    assert len(my_accounting_export_jobs(user=farmer)['items'])==1
    assert my_accounting_export_jobs(user=stranger)['items']==[]
    with pytest.raises(HTTPException) as exc:
        prepare_accounting_export(940001,user=stranger)
    assert exc.value.status_code==404


def test_postgres_job_insert_translation():
    assert translate_sql('INSERT INTO accounting_export_jobs(invoice_draft_id) VALUES(?) ON CONFLICT(invoice_draft_id) DO NOTHING').count('%s')==1

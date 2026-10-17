import pytest
from fastapi import HTTPException
from backend.app import db, create_invoice_draft, my_invoice_drafts, InvoiceDraftIn

def test_invoice_draft_review_and_isolation():
    with db() as con:
        # Reuse an existing seller draft, if tests ran earlier; otherwise create data directly.
        con.execute("INSERT INTO users(id,email,password_hash,role) VALUES(900001,'invoice-farmer@test.local','x','rolnik') ON CONFLICT DO NOTHING")
        con.execute("INSERT INTO users(id,email,password_hash,role) VALUES(900002,'invoice-buyer@test.local','x','klient') ON CONFLICT DO NOTHING")
        con.execute("INSERT INTO products(id,farmer_id,name,price_grosze,delivery_grosze,stock) VALUES(900001,900001,'Produkt testowy',9999,0,10) ON CONFLICT DO NOTHING")
        con.execute("""INSERT INTO orders(id,buyer_id,farmer_id,product_id,quantity,subtotal_grosze,delivery_grosze,total_grosze,fulfillment,status,pickup_code,pin_hash,created_at)
          VALUES(900001,900002,900001,900001,1,9999,0,9999,'odbior','new','INV-900001','hash','2026-01-01') ON CONFLICT DO NOTHING""")
        con.execute("""INSERT INTO commission_drafts(id,order_id,farmer_id,basis_grosze,rate_basis_points,commission_grosze,created_at)
          VALUES(900001,900001,900001,9999,500,500,'2026-01-01') ON CONFLICT DO NOTHING""")
    user={'id':900001,'role':'rolnik'}
    payload=InvoiceDraftIn(commission_draft_id=900001,seller_name='WiejskaPaka Test',seller_nip='1234567890',buyer_name='Gospodarstwo Test')
    result=create_invoice_draft(payload,user=user)
    assert result['net_grosze']==500 and result['vat_grosze'] is None and not result['issued']
    assert any(x['commission_draft_id']==900001 for x in my_invoice_drafts(user=user)['items'])
    with pytest.raises(HTTPException) as duplicate:
        create_invoice_draft(payload,user=user)
    assert duplicate.value.status_code==409
    with pytest.raises(HTTPException) as hidden:
        create_invoice_draft(payload,user={'id':900002,'role':'rolnik'})
    assert hidden.value.status_code==404
    assert my_invoice_drafts(user={'id':900002,'role':'rolnik'})['items']==[]

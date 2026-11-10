"""Checkout and message share one real HTTP transaction; no SMTP calls."""
from contextlib import closing
import sqlite3
import pytest
from tests.test_email_verification_http import enabled, queued
from tests.test_purchase_record_http_restart import server, account


def setup(client,verified,database,keys):
    farmer=account(client,'rolnik');buyer=account(client,'klient')
    if verified:
        assert client.post('/auth/email-verification/request',headers=buyer).status_code==202
        assert client.post('/auth/email-verification/confirm',headers=buyer,json={'token':queued(database,keys).token}).status_code==200
    p=client.post('/products',headers=farmer,json={'name':'Pomidor','price_grosze':349,'delivery_grosze':501,'stock':5})
    assert p.status_code==201
    return buyer,p.json()['id']


def order(client,buyer,pid,cart):
    body={'fulfillment':'dostawa','delivery_city':'Legnica','delivery_street':'Testowa 1','delivery_postal_code':'59-220'}
    if not cart:body.update(product_id=pid,quantity=1)
    return client.post('/cart/checkout-test' if cart else '/orders',json=body,
        headers={**buyer,'Idempotency-Key':'atomic-mail-checkout-001'})


@pytest.mark.parametrize('cart',[False,True])
@pytest.mark.parametrize('verified',[False,True])
def test_atomic_capture_one_job_and_repeated_checkout(enabled,cart,verified):
    database,keys,key_path=enabled
    with server(database,verification_keys=key_path,order_mail=True) as client:
        buyer,pid=setup(client,verified,database,keys)
        if cart:assert client.put('/cart/items',headers=buyer,json={'product_id':pid,'quantity':1}).status_code==200
        first=order(client,buyer,pid,cart);assert first.status_code==201,first.text
        second=order(client,buyer,pid,cart);assert second.status_code==201
        assert first.json()==second.json()
        with closing(sqlite3.connect(database)) as con:
            assert con.execute('SELECT count(*) FROM orders').fetchone()[0]==1
            assert con.execute('SELECT count(*) FROM order_mail_outbox').fetchone()[0]==int(verified)
            assert con.execute('SELECT stock FROM products WHERE id=?',(pid,)).fetchone()[0]==4
        assert first.json()['total_grosze']==850
        if verified:
            from backend import order_mail_outbox as outbox, email_ownership as proof
            from backend.checkout_vault import Vault,read_ring
            from backend.smtp_reset_transport import outcome
            from tests.test_sqlite_recovery_rehearsal import key_path as checkout_key_path
            import time
            def connect():
                con=sqlite3.connect(database);con.row_factory=sqlite3.Row;return con
            def submit(recipient,purchase,**kwargs):
                assert purchase.total_grosze==850 and purchase.delivery_grosze==501
                assert purchase.pin==first.json()['shipment_pin_test_only' if cart else 'pin_test_only']
                assert kwargs=={'email_verified':True}
                return outcome('ACCEPTED',accepted=True)
            vault=Vault(*read_ring(checkout_key_path(database)))
            assert outbox.dispatch_once(connect,vault,submit,proof.verified_recipient,clock=lambda:int(time.time()))=='ACCEPTED'
            assert outbox.dispatch_once(connect,vault,lambda *a,**kw:pytest.fail('Duplicate mail'),proof.verified_recipient,clock=lambda:int(time.time()))=='IDLE' 


@pytest.mark.parametrize('cart',[False,True])
def test_mail_insert_failure_rolls_back_whole_purchase(enabled,cart):
    database,keys,key_path=enabled
    with server(database,verification_keys=key_path,order_mail=True) as client:
        buyer,pid=setup(client,True,database,keys)
        if cart:assert client.put('/cart/items',headers=buyer,json={'product_id':pid,'quantity':1}).status_code==200
        with closing(sqlite3.connect(database)) as con:
            con.execute("CREATE TRIGGER fail_mail BEFORE INSERT ON order_mail_outbox BEGIN SELECT RAISE(ABORT,'synthetic mail failure'); END")
        assert order(client,buyer,pid,cart).status_code==500
        with closing(sqlite3.connect(database)) as con:
            assert con.execute('SELECT count(*) FROM orders').fetchone()[0]==0
            assert con.execute('SELECT count(*) FROM checkout_idempotency').fetchone()[0]==0
            assert con.execute('SELECT count(*) FROM order_mail_outbox').fetchone()[0]==0
            assert con.execute('SELECT stock FROM products WHERE id=?',(pid,)).fetchone()[0]==5
            if cart:assert con.execute('SELECT count(*) FROM saved_cart_items').fetchone()[0]==1

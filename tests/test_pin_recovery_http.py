"""Actual TCP and process restarts, no browser or native PostgreSQL claim."""
from contextlib import closing
from datetime import datetime,timedelta,timezone
import sqlite3
import os
import pytest
from tests.test_purchase_record_http_restart import server,setup,checkout
from backend.checkout_vault import rotate_ring, CheckoutStorageError
PASSWORD='Disposable-private-record-123!'


@pytest.mark.parametrize('cart',[False,True])
def test_lost_response_and_old_link_migration_after_restart_and_key_rotation(tmp_path,cart):
    database=tmp_path/'recovery.sqlite3'
    with server(database) as client:
        farmer,buyer,products=setup(client)
        _,_,original=checkout(client,buyer,products,cart)
        expected=original['shipment_pin_test_only' if cart else 'pin_test_only']
        ids=[o['id'] for o in original['orders']] if cart else [original['id']]
    # Simulate an upgrade from the previous release: encrypted cache, no link tables.
    with closing(sqlite3.connect(database)) as con, con:
        con.execute('DROP TABLE checkout_pin_links');con.execute('DROP TABLE checkout_pin_access')
    if os.name == 'posix':
        rotate_ring(str(database)+'.checkout-key')
    else:
        with pytest.raises(CheckoutStorageError, match='POSIX'):
            rotate_ring(str(database)+'.checkout-key')
    with server(database) as client:
        history=client.get('/orders/me',headers=buyer);assert history.status_code==200
        assert {o['id'] for o in history.json()}==set(ids)
        url=f'/orders/{ids[0]}/recover-pin-test'
        r=client.post(url,headers=buyer,json={'password':PASSWORD})
        assert r.status_code==200,r.text
        assert r.json()['pin_test_only']==expected and r.json()['order_ids']==ids
        assert r.headers['cache-control']=='no-store'
        assert client.post(url,json={'password':PASSWORD}).status_code==401
        assert client.post(url,headers=farmer,json={'password':PASSWORD}).status_code==403
    with closing(sqlite3.connect(database)) as con, con:
        assert con.execute('SELECT COUNT(*) FROM orders').fetchone()[0]==len(ids)
        assert con.execute('SELECT COUNT(*) FROM checkout_pin_links').fetchone()[0]==len(ids)
        assert 'pin_test_only' not in con.execute('SELECT response_json FROM checkout_idempotency').fetchone()[0]


def test_wrong_password_budget_survives_process_restart(tmp_path):
    database=tmp_path/'attempts.sqlite3'
    with server(database) as client:
        farmer,buyer,products=setup(client);_,_,original=checkout(client,buyer,products,False)
        url=f'/orders/{original["id"]}/recover-pin-test'
        for _ in range(3):assert client.post(url,headers=buyer,json={'password':'wrong'}).status_code==401
    with server(database) as client:
        for _ in range(2):assert client.post(url,headers=buyer,json={'password':'wrong'}).status_code==401
        limited=client.post(url,headers=buyer,json={'password':PASSWORD})
        assert limited.status_code==429 and int(limited.headers['retry-after'])>0
        assert 'pin_test_only' not in limited.text


@pytest.mark.parametrize('cart',[False,True])
@pytest.mark.parametrize('outcome',['receipt','courier_fault'])
def test_recovered_pin_real_delivery_full_refund_or_payout(tmp_path,cart,outcome):
    """Use the recovered value for actual HTTP receipt, then reconcile grosze."""
    from decimal import Decimal,ROUND_HALF_UP
    from uuid import uuid4
    from tests.test_purchase_record_http_restart import account
    database=tmp_path/'financial-recovery.sqlite3'
    with server(database) as client:
        farmer,buyer,products=setup(client);courier=account(client,'dostawca')
        cid=client.get('/auth/me',headers=courier).json()['id']
        _,ids,original=checkout(client,buyer,products,cart)
        target=f'/shipments/{original["shipment_id"]}' if cart else f'/orders/{ids[0]}'
        total=1001 if cart else 700
        assert (original['total_grosze'],original.get('delivery_grosze',501))==(total,501)
        def event(oid,who,kind,event_id=None):
            r=client.post(f'/test/payments/{oid}/events',headers=who,json={'event_id':event_id or uuid4().hex,'event_type':kind})
            assert r.status_code==200,r.text
            return r.json()
        for oid in ids:event(oid,buyer,'payment_success_test')
        assert client.post(target+'/assign-courier-test',headers=farmer,json={'courier_id':cid}).status_code==200
        assert client.post(target+'/dispatch-test',headers=farmer).status_code==200
        recovered=client.post(target+'/recover-pin-test',headers=buyer,json={'password':PASSWORD})
        assert recovered.status_code==200,recovered.text
        pin=recovered.json()['pin_test_only']
        assert len(pin)==6 and pin.isascii() and pin.isdigit()
        if outcome=='receipt':
            assert client.post(target+'/confirm',headers=courier,json={'pin':pin,'checked_goods':False}).status_code==422
            wrong='999999' if pin!='999999' else '888888'
            bad=client.post(target+'/confirm',headers=courier,json={'pin':wrong,'checked_goods':True})
            assert bad.status_code==200 and bad.json()['remaining_attempts']==4
            again=client.post(target+'/recover-pin-test',headers=buyer,json={'password':PASSWORD})
            assert again.status_code==200 and again.json()['pin_test_only']==pin
            done=client.post(target+'/confirm',headers=courier,json={'pin':again.json()['pin_test_only'],'checked_goods':True})
            assert done.status_code==200 and done.json()['confirmed']
            assert client.post(target+'/confirm',headers=courier,json={'pin':pin,'checked_goods':True}).status_code==409
            for oid in ids:
                event(oid,farmer,'order_completed_test')
                key=uuid4().hex;paid=event(oid,farmer,'weekly_payout_test',key)
                assert event(oid,farmer,'weekly_payout_test',key)==paid
                commission=int((Decimal(paid['products_grosze'])*Decimal('0.05')).quantize(Decimal(1),rounding=ROUND_HALF_UP))
                assert paid['commission_grosze']==commission
                assert paid['payout_grosze']==paid['total_grosze']-commission and paid['refund_grosze']==0
        else:
            if cart:
                failure=client.post(target+'/courier-failure-test',headers=farmer,json={'reason':'dostawca_nie_przyjechal'})
                assert failure.status_code==200 and failure.json()['refund_grosze']==total
                repeated=client.post(target+'/courier-failure-test',headers=farmer,json={'reason':'dostawca_nie_przyjechal'})
                assert repeated.status_code==200 and repeated.json()['already_processed']
            else:
                key=uuid4().hex;refunded=event(ids[0],farmer,'delivery_failed_by_courier_test',key)
                assert event(ids[0],farmer,'delivery_failed_by_courier_test',key)==refunded
            assert client.post(target+'/confirm',headers=courier,json={'pin':pin,'checked_goods':True}).status_code==409
        assert client.post(target+'/recover-pin-test',headers=buyer,json={'password':PASSWORD}).status_code==409
        assert client.get('/couriers/me/active-addresses',headers=courier).json()==[]
        payments=[client.get(f'/test/payments/{oid}',headers=buyer).json() for oid in ids]
        assert sum(p['total_grosze'] for p in payments)==total
        assert sum(p['delivery_grosze'] for p in payments)==501
        assert all(type(p[k]) is int for p in payments for k in ('total_grosze','refund_grosze','payout_grosze','commission_grosze'))
        if outcome=='courier_fault':
            assert sum(p['refund_grosze'] for p in payments)==total
            assert sum(p['payout_grosze'] for p in payments)==0

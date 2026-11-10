"""Abrupt process death, replay and full-refund durability over actual TCP HTTP.

These are SQLite crash-recovery tests, not a power-loss/fsync guarantee and
not native PostgreSQL acceptance. Only explicitly spawned children are killed.
"""
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from pathlib import Path
import os
import socket
import sqlite3
import subprocess
import sys
import time
from uuid import uuid4
import httpx
import pytest
from scripts.run_phone_demo import demo_environment
from tests.test_purchase_record_http_restart import setup,account
ROOT=Path(__file__).resolve().parents[1]


@contextmanager
def killable_server(database):
    env=demo_environment(os.environ,database);env['WP_ENABLE_TEST_PAYMENTS']='1'
    with socket.socket() as sock:
        sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
    process=subprocess.Popen([sys.executable,'-m','uvicorn','backend.app:app','--host','127.0.0.1','--port',str(port),'--no-access-log'],
        cwd=ROOT,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    try:
        with httpx.Client(base_url=f'http://127.0.0.1:{port}',timeout=10,trust_env=False) as c:
            for _ in range(150):
                assert process.poll() is None,'Disposable server exited'
                try:
                    if c.get('/health').status_code==200:break
                except httpx.TransportError:pass
                time.sleep(.05)
            else:raise AssertionError('Disposable server startup timeout')
            yield c,process
    finally:
        if process.poll() is None:process.terminate()
        try:process.wait(timeout=5)
        except subprocess.TimeoutExpired:process.kill();process.wait(timeout=5)


def kill_during_request(process,operation,delay):
    if delay is None:
        response=operation();assert response.status_code in (200,201),response.text
        process.kill();process.wait(timeout=5);return response
    def uncertain():
        try:return operation()
        except httpx.TransportError:return None
    with ThreadPoolExecutor(max_workers=1) as pool:
        future=pool.submit(uncertain)
        time.sleep(delay)
        process.kill();process.wait(timeout=5)
        response=future.result(timeout=12)
    if response is not None:assert response.status_code in (200,201),response.text
    return response


@pytest.mark.parametrize('cart',[False,True])
@pytest.mark.parametrize('delay',[0.0,0.05])
def test_abrupt_checkout_and_refund_crash_never_duplicate_money_or_stock(tmp_path,cart,delay):
    database=tmp_path/'crash.sqlite3';key=uuid4().hex
    with killable_server(database) as (c,process):
        farmer,buyer,products=setup(c);courier=account(c,'dostawca')
        cid=c.get('/auth/me',headers=courier).json()['id']
        if cart:
            for pid in products:assert c.put('/cart/items',headers=buyer,json={'product_id':pid,'quantity':1}).status_code==200
        body={'fulfillment':'dostawa','delivery_city':'Syntetyczne Miasto','delivery_street':'Testowa 1','delivery_postal_code':'45-001'}
        if not cart:body.update(product_id=products[0],quantity=1)
        url='/cart/checkout-test' if cart else '/orders';headers={**buyer,'Idempotency-Key':key}
        uncertain=kill_during_request(process,lambda:c.post(url,headers=headers,json=body),delay)
    key_path=Path(str(database)+'.checkout-key');encryption_key=key_path.read_bytes()
    with killable_server(database) as (c,process):
        replay=c.post(url,headers=headers,json=body);assert replay.status_code==201,replay.text
        result=replay.json()
        if uncertain is not None:assert uncertain.json()==result
        assert c.post(url,headers=headers,json=body).json()==result
        ids=[o['id'] for o in result['orders']] if cart else [result['id']]
        assert len(ids)==(2 if cart else 1) and len(set(ids))==len(ids)
        total=1001 if cart else 700;assert result['total_grosze']==total
        with sqlite3.connect(database) as con:
            assert con.execute('SELECT COUNT(*) FROM orders').fetchone()[0]==len(ids)
            assert con.execute('SELECT COUNT(*) FROM checkout_idempotency').fetchone()[0]==1
            assert con.execute('SELECT COUNT(*) FROM order_purchase_records').fetchone()[0]==len(ids)
            assert con.execute('SELECT SUM(delivery_grosze),SUM(total_grosze) FROM orders').fetchone()==(501,total)
            assert con.execute('SELECT stock FROM products WHERE id=?',(products[0],)).fetchone()[0]==99
            assert con.execute('SELECT stock FROM products WHERE id=?',(products[1],)).fetchone()[0]==(99 if cart else 100)
            assert con.execute('PRAGMA integrity_check').fetchone()[0]=='ok' and not con.execute('PRAGMA foreign_key_check').fetchall()
        target=f'/shipments/{result["shipment_id"]}' if cart else f'/orders/{ids[0]}'
        pin=result['shipment_pin_test_only' if cart else 'pin_test_only']
        recovery=c.post(target+'/recover-pin-test',headers=buyer,json={'password':'Disposable-private-record-123!'})
        assert recovery.status_code==200 and recovery.json()['pin_test_only']==pin
        for oid in ids:
            pay=c.post(f'/test/payments/{oid}/events',headers=buyer,json={'event_id':uuid4().hex,'event_type':'payment_success_test'})
            assert pay.status_code==200,pay.text
        assert c.post(target+'/assign-courier-test',headers=farmer,json={'courier_id':cid}).status_code==200
        assert c.post(target+'/dispatch-test',headers=farmer).status_code==200
        if cart:
            refund_url=target+'/courier-failure-test';refund_body={'reason':'dostawca_nie_przyjechal'}
        else:
            refund_url=f'/test/payments/{ids[0]}/events';refund_body={'event_id':uuid4().hex,'event_type':'delivery_failed_by_courier_test'}
        kill_during_request(process,lambda:c.post(refund_url,headers=farmer,json=refund_body),delay)
    with killable_server(database) as (c,process):
        refund=c.post(refund_url,headers=farmer,json=refund_body);assert refund.status_code==200,refund.text
        assert refund.json()['refund_grosze']==total
        assert c.post(refund_url,headers=farmer,json=refund_body).status_code==200
        assert c.post(target+'/confirm',headers=courier,json={'pin':pin,'checked_goods':True}).status_code==409
        assert c.post(target+'/recover-pin-test',headers=buyer,json={'password':'Disposable-private-record-123!'}).status_code==409
        assert c.get('/couriers/me/active-addresses',headers=courier).json()==[]
        payments=[c.get(f'/test/payments/{oid}',headers=buyer).json() for oid in ids]
        assert all(p['state']=='refunded_test' and p['payout_grosze']==0 for p in payments)
        assert sum(p['refund_grosze'] for p in payments)==total
        # Even after refund, retrying the old key must never create another order.
        assert c.post(url,headers=headers,json=body).json()==result
        assert key_path.read_bytes()==encryption_key
        process.kill();process.wait(timeout=5)
    with sqlite3.connect(database) as con:
        assert con.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        assert not con.execute('PRAGMA foreign_key_check').fetchall()
        assert con.execute('SELECT COUNT(*) FROM orders').fetchone()[0]==len(ids)
        assert con.execute("SELECT COUNT(*) FROM payment_simulation_events WHERE event_type='delivery_failed_by_courier_test'").fetchone()[0]==len(ids)
        assert con.execute('SELECT SUM(refund_grosze),SUM(payout_grosze) FROM payment_simulations').fetchone()==(total,0)


@pytest.mark.parametrize('after_ack',[False,True])
def test_abrupt_password_change_is_atomic_with_all_session_revocation(tmp_path,after_ack):
    database=tmp_path/'password-crash.sqlite3';old='Disposable-private-record-123!';new='New-private-crash-password!'
    with killable_server(database) as (c,process):
        farmer,buyer,products=setup(c)
        email=c.get('/auth/me',headers=buyer).json()['email']
        extra=c.post('/auth/login',json={'email':email,'password':old});assert extra.status_code==200
        second={'Authorization':'Bearer '+extra.json()['access_token']}
        key=uuid4().hex;body={'product_id':products[0],'quantity':1,'fulfillment':'dostawa',
            'delivery_city':'Syntetyczne Miasto','delivery_street':'Testowa 1','delivery_postal_code':'45-001'}
        made=c.post('/orders',headers={**buyer,'Idempotency-Key':key},json=body);assert made.status_code==201
        original=made.json();oid=original['id']
        record=c.get(f'/orders/{oid}/purchase-record',headers=buyer).json()
        key_path=Path(str(database)+'.checkout-key');encryption_key=key_path.read_bytes()
        recovered=c.post(f'/orders/{oid}/recover-pin-test',headers=buyer,json={'password':old});assert recovered.status_code==200
        result=kill_during_request(process,lambda:c.post('/auth/change-password',headers=buyer,
            json={'current_password':old,'new_password':new}),None if after_ack else .02)
    with killable_server(database) as (c,process):
        old_login=c.post('/auth/login',json={'email':email,'password':old})
        new_login=c.post('/auth/login',json={'email':email,'password':new})
        assert sorted(r.status_code for r in (old_login,new_login))==[200,401]
        committed=new_login.status_code==200
        if after_ack or result is not None:assert committed
        for previous in (buyer,second):assert c.get('/auth/me',headers=previous).status_code==(401 if committed else 200)
        assert c.get('/auth/me',headers=farmer).status_code==200
        successful=new_login if committed else old_login
        current={'Authorization':'Bearer '+successful.json()['access_token']}
        assert c.get(f'/orders/{oid}/purchase-record',headers=current).json()==record
        replay=c.post('/orders',headers={**current,'Idempotency-Key':key},json=body)
        assert replay.status_code==201 and replay.json()==original
        pin=c.post(f'/orders/{oid}/recover-pin-test',headers=current,json={'password':new if committed else old})
        assert pin.status_code==200 and pin.json()['pin_test_only']==original['pin_test_only']
        assert key_path.read_bytes()==encryption_key
    with sqlite3.connect(database) as con:
        assert con.execute('PRAGMA integrity_check').fetchone()[0]=='ok' and not con.execute('PRAGMA foreign_key_check').fetchall()
        uid=con.execute('SELECT id FROM users WHERE email=?',(email,)).fetchone()[0]
        attempts=con.execute('SELECT attempts FROM password_change_access WHERE user_id=?',(uid,)).fetchone()
        assert attempts==((1,) if committed else None)
        assert con.execute('SELECT attempts FROM checkout_pin_access WHERE buyer_id=?',(uid,)).fetchone()[0]==2
        assert con.execute('SELECT COUNT(*) FROM orders').fetchone()[0]==1

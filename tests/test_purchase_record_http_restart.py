"""Real TCP restart durability and read/refund races on disposable SQLite."""
from contextlib import closing
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

ROOT=Path(__file__).resolve().parents[1]


@contextmanager
def server(database):
    env=demo_environment(os.environ,database);env['WP_ENABLE_TEST_PAYMENTS']='1'
    with socket.socket() as sock:
        sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
    process=subprocess.Popen([sys.executable,'-m','uvicorn','backend.app:app','--host','127.0.0.1','--port',str(port),'--no-access-log'],
                             cwd=ROOT,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    try:
        with httpx.Client(base_url=f'http://127.0.0.1:{port}',timeout=15,trust_env=False) as client:
            for _ in range(100):
                assert process.poll() is None,'Disposable server exited'
                try:
                    if client.get('/health').status_code==200:break
                except httpx.TransportError:pass
                time.sleep(.05)
            else:raise AssertionError('Disposable HTTP startup timeout')
            yield client
    finally:
        process.terminate()
        try:process.wait(timeout=10)
        except subprocess.TimeoutExpired:process.kill();process.wait(timeout=5)


def account(client,role):
    body={'email':uuid4().hex+'@example.invalid','password':'Disposable-private-record-123!','role':role}
    assert client.post('/auth/register',json=body).status_code==201
    token=client.post('/auth/login',json=body).json()['access_token']
    return {'Authorization':'Bearer '+token}


def setup(client):
    farmer=account(client,'rolnik');buyer=account(client,'klient')
    products=[]
    for amount in (199,301):
        r=client.post('/products',headers=farmer,json={'name':'Trwała oferta','price_grosze':amount,'delivery_grosze':501,'stock':100})
        assert r.status_code==201;products.append(r.json()['id'])
    return farmer,buyer,products


def checkout(client,buyer,products,cart):
    body={'fulfillment':'dostawa','delivery_city':'Prywatne miasto','delivery_street':'Prywatna 99','delivery_postal_code':'45-001'}
    if cart:
        for pid in products:assert client.put('/cart/items',headers=buyer,json={'product_id':pid,'quantity':1}).status_code==200
        url='/cart/checkout-test'
    else:body.update(product_id=products[0],quantity=1);url='/orders'
    r=client.post(url,headers={**buyer,'Idempotency-Key':uuid4().hex},json=body)
    assert r.status_code==201,r.text
    data=r.json();ids=[o['id'] for o in data['orders']] if cart else [data['id']]
    record_url=f'/shipments/{data["shipment_id"]}/purchase-record' if cart else f'/orders/{ids[0]}/purchase-record'
    return record_url,ids,data


def test_record_and_sql_guards_survive_actual_process_restart(tmp_path):
    database=tmp_path/'restart.sqlite3'
    with server(database) as client:
        farmer,buyer,products=setup(client)
        url,ids,receipt=checkout(client,buyer,products,True)
        before=client.get(url,headers=buyer).json()
        assert before['original_available']
    with closing(sqlite3.connect(database)) as con, con:
        records=con.execute('SELECT * FROM order_purchase_records ORDER BY order_id').fetchall()
    with server(database) as client:
        # Login session and original record both remain valid after a clean restart.
        r=client.get(url,headers=buyer);assert r.status_code==200,r.text
        assert r.json()==before
        for pid in products:
            assert client.patch(f'/products/mine/{pid}',headers=farmer,json={'name':'Po restarcie','price_grosze':9999}).status_code==200
        assert client.get(url,headers=buyer).json()==before
        assert client.post('/auth/logout',headers=buyer).status_code==200
        assert client.get(url,headers=buyer).status_code==401
    with server(database) as client:
        assert client.get(url,headers=buyer).status_code==401
        assert client.get(url,headers=farmer).json()==before
    with closing(sqlite3.connect(database)) as con, con:
        assert con.execute('SELECT * FROM order_purchase_records ORDER BY order_id').fetchall()==records
        for sql in ('UPDATE order_purchase_records SET product_name=product_name WHERE order_id=?',
                    'DELETE FROM order_purchase_records WHERE order_id=?',
                    'INSERT OR REPLACE INTO order_purchase_records SELECT * FROM order_purchase_records WHERE order_id=?'):
            with pytest.raises(sqlite3.IntegrityError):con.execute(sql,(ids[0],))
        assert con.execute('PRAGMA integrity_check').fetchone()[0]=='ok'


@pytest.mark.parametrize('cart',[False,True])
def test_actual_http_read_refund_race_never_returns_partial_financial_state(tmp_path,cart):
    with server(tmp_path/'race.sqlite3') as client:
        farmer,buyer,products=setup(client)
        for _ in range(8):
            url,ids,result=checkout(client,buyer,products,cart)
            for oid in ids:
                assert client.post(f'/test/payments/{oid}/events',headers=buyer,
                    json={'event_id':uuid4().hex,'event_type':'payment_success_test'}).status_code==200
            original=client.get(url,headers=buyer).json()
            cancel=f'/shipments/{result["shipment_id"]}/cancel-paid-test' if cart else f'/orders/{ids[0]}/cancel-paid-test'
            def action(index):
                return client.post(cancel,headers=buyer) if index==4 else client.get(url,headers=buyer)
            with ThreadPoolExecutor(max_workers=4) as pool:responses=list(pool.map(action,range(12)))
            for index,response in enumerate(responses):
                assert response.status_code==200,response.text
                assert response.headers['cache-control']=='no-store'
                if index==4:
                    assert response.json()['refund_grosze']==(1001 if cart else 700);continue
                data=response.json()
                assert data['original']==original['original']
                entries=data['orders'] if cart else [data]
                for entry in entries:
                    assert all(key not in str(entry) for key in ('pin_test_only','pin_hash','Prywatna 99','phone'))
                    current=entry['current'];state=current['payment_state_test']
                    assert state in ('paid_test','refunded_test')
                    if state=='paid_test':
                        assert current['refund_grosze']==0 and current['status']=='oczekuje_na_platnosc_testowa'
                    else:
                        assert current['refund_grosze']==entry['original']['total_grosze']
                        assert current['status']=='anulowane_testowo'
                assert len({e['current']['payment_state_test'] for e in entries})==1
            after=client.get(url,headers=buyer).json()
            assert after['original']==original['original']

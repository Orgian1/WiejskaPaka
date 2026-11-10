"""Real HTTP authorization, concurrency, retries and no financial side effects."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
import json
import sqlite3
from uuid import uuid4
import pytest
from tests.test_purchase_record_http_restart import server,account,setup,checkout
from tests.test_admin_seller_review import create_admin


def exercise_support(client,admin):
    farmer,buyer,products=setup(client)
    outsider=account(client,'klient');other_farmer=account(client,'rolnik');courier=account(client,'dostawca')
    _,ids,_=checkout(client,buyer,products,True)
    standalone=client.post('/orders',headers={**buyer,'Idempotency-Key':uuid4().hex},json={'product_id':products[0],'quantity':1,'fulfillment':'dostawa','delivery_city':'Legnica','delivery_street':'Fikcyjna 1','delivery_postal_code':'59-220'}).json()
    url='/test/support/cases'
    assert client.get(url).status_code==401
    assert client.get(url,headers=courier).status_code==403
    assert client.get(url+'?limit=51',headers=buyer).status_code==422
    assert client.get(url+'?status=unknown',headers=buyer).status_code==422
    before_orders=client.get('/orders/me',headers=buyer).json()
    before_products=client.get('/products/mine',headers=farmer).json()
    payment_ids=ids+[standalone['id']]
    before_payments=[client.get(f'/test/payments/{oid}',headers=buyer).json() for oid in payment_ids]
    payload={'kind':'order','target_id':str(ids[0]),'category':'product','description':'<img src=x onerror=alert(1)> Fikcyjny problem produktu','request_id':str(uuid4())}
    assert client.post(url,headers=outsider,json=payload).status_code==404
    for actor in (farmer,courier,admin):assert client.post(url,headers=actor,json=payload).status_code==403
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(lambda _:client.post(url,headers=buyer,json=payload),range(2)))
    assert [r.status_code for r in results]==[201,201]
    case=results[0].json()['case'];cid=case['id'];path=url+'/'+cid
    assert case['kind']=='shipment' and case['revision']==1
    assert all(r.json()['case']['id']==cid for r in results)
    assert client.post(url,headers=buyer,json={**payload,'description':'Zmieniona fikcyjna treść'}).status_code==409
    assert client.post(url,headers=buyer,json={**payload,'request_id':str(uuid4()),'target_id':'9223372036854775808'}).status_code==404
    for actor in (outsider,other_farmer,courier):
        assert client.get(path,headers=actor).status_code in (403,404)
        assert client.post(path+'/replies',headers=actor,json={'message':'Próba obcego konta','request_id':str(uuid4()),'expected_revision':1}).status_code in (403,404)
    for actor in (buyer,farmer,admin):
        data=client.get(path,headers=actor).json();assert data['case']['id']==cid and len(data['events'])==1
        row=next(x for x in client.get(url,headers=actor).json()['cases'] if x['id']==cid)
        assert 'description' not in row
        text=json.dumps(data);assert 'delivery_street' not in text and 'pin_test_only' not in text and 'buyer_id' not in text
    assert client.get(url,headers=outsider).json()['cases']==[]
    reply={'message':'Fikcyjna odpowiedź rolnika','request_id':str(uuid4()),'expected_revision':1}
    assert client.post(path+'/replies',headers=farmer,json={**reply,'status':'closed_test'}).status_code==403
    with ThreadPoolExecutor(max_workers=2) as pool:
        replies=list(pool.map(lambda _:client.post(path+'/replies',headers=farmer,json=reply),range(2)))
    assert [r.status_code for r in replies]==[200,200]
    assert all(r.json()['case']['revision']==2 for r in replies)
    assert client.post(path+'/replies',headers=farmer,json={**reply,'message':'Zmieniona odpowiedź'}).status_code==409
    assert client.post(path+'/replies',headers=buyer,json={**reply,'request_id':str(uuid4())}).status_code==409
    with ThreadPoolExecutor(max_workers=2) as pool:
        decisions=list(pool.map(lambda state:client.post(path+'/replies',headers=admin,json={'message':'Fikcyjna decyzja administracyjna','request_id':str(uuid4()),'expected_revision':2,'status':state}),('in_review','closed_test')))
    assert sorted(r.status_code for r in decisions)==[200,409]
    current=client.get(path,headers=admin).json()['case']
    if current['status']=='closed_test':
        response=client.post(path+'/replies',headers=admin,json={'message':'Ponowne otwarcie po wyścigu decyzji','request_id':str(uuid4()),'expected_revision':current['revision'],'status':'in_review'})
        assert response.status_code==200;current=response.json()['case']
    for state in ('closed_test','in_review'):
        response=client.post(path+'/replies',headers=admin,json={'message':'Fikcyjna zmiana stanu','request_id':str(uuid4()),'expected_revision':current['revision'],'status':state})
        assert response.status_code==200;current=response.json()['case']
        if state=='closed_test':
            assert client.post(path+'/replies',headers=buyer,json={'message':'Próba po zamknięciu','request_id':str(uuid4()),'expected_revision':current['revision']}).status_code==409
    # More than one history page; no event may disappear or repeat.
    for _ in range(18):
        response=client.post(path+'/replies',headers=buyer,json={'message':'Fikcyjna dodatkowa informacja','request_id':str(uuid4()),'expected_revision':current['revision']})
        assert response.status_code==200;current=response.json()['case']
    history=client.get(path,headers=buyer).json();assert len(history['events'])==20 and history['has_older_events']
    older=client.get(path+'?before_revision='+str(history['events'][0]['revision']),headers=buyer).json()
    revisions=[x['revision'] for x in older['events']+history['events']]
    assert revisions==list(range(1,current['revision']+1)) and not older['has_older_events']
    # A separate standalone order stays an order case.
    result=client.post(url,headers=buyer,json={**payload,'request_id':str(uuid4()),'target_id':str(standalone['id'])})
    assert result.status_code==201 and result.json()['case']['kind']=='order'
    page=client.get(url+'?limit=1',headers=buyer).json();assert len(page['cases'])==1 and page['has_more']
    assert len(client.get(url+'?limit=1&offset=1',headers=buyer).json()['cases'])==1
    assert client.get('/orders/me',headers=buyer).json()==before_orders
    assert client.get('/products/mine',headers=farmer).json()==before_products
    assert [client.get(f'/test/payments/{oid}',headers=buyer).json() for oid in payment_ids]==before_payments
    return cid,buyer


def test_sqlite_real_support_cases(tmp_path):
    database=tmp_path/'support.sqlite'
    with server(database) as client:
        def promote(uid):
            with closing(sqlite3.connect(database)) as con,con:con.execute("UPDATE users SET role='admin' WHERE id=?",(uid,))
        admin,_=create_admin(client,promote)
        cid,buyer=exercise_support(client,admin)
    with server(database) as client:
        assert client.get('/test/support/cases/'+cid,headers=buyer).json()['case']['revision']>20
    with closing(sqlite3.connect(database)) as con:
        assert con.execute('PRAGMA foreign_key_check').fetchall()==[]
        assert con.execute('SELECT count(*) FROM support_cases').fetchone()[0]==2


@pytest.mark.parametrize('field,value',[('description','short'),('request_id','bad'),('category','refund'),('kind','anything')])
def test_invalid_support_payload_is_rejected(tmp_path,field,value):
    with server(tmp_path/'validation.sqlite') as client:
        buyer=account(client,'klient')
        body={'kind':'order','target_id':'1','category':'other','description':'Fikcyjny opis problemu','request_id':str(uuid4()),field:value}
        assert client.post('/test/support/cases',headers=buyer,json=body).status_code==422


def test_support_is_disabled_without_explicit_test_flag(monkeypatch):
    from fastapi.testclient import TestClient
    from backend.app import app
    monkeypatch.setenv('WP_ENABLE_TEST_PAYMENTS','0')
    with TestClient(app) as client:
        buyer=account(client,'klient')
        assert client.get('/test/support/cases',headers=buyer).status_code==404
        body={'kind':'order','target_id':'1','category':'other','description':'Fikcyjny opis problemu','request_id':str(uuid4())}
        assert client.post('/test/support/cases',headers=buyer,json=body).status_code==404

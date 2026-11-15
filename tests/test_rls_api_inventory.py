"""Additional HTTP coverage on the same restricted RLS API used by native gates."""
import json
import os
from pathlib import Path
import re
from uuid import uuid4
import pytest
from tests.test_postgres_full_api_optin import pg_api,pg_photo_api,pg_seller_api,pg_address_delivery_api,pg_units_api,register,product,inspection_connect

pytestmark=pytest.mark.skipif(os.environ.get('WP_TEST_ENABLE_RLS')!='1',reason='Run scripts.run_rls_api_gate for the complete RLS database fixture')


def test_all_private_routes_reject_anonymous_sql_context(pg_api):
    client,_=pg_api
    inventory=json.loads((Path(__file__).resolve().parents[1]/'docs/AUDYT_TRAS_SECURITY_2026-11-15.json').read_text())
    rows=[r for r in inventory['routes'] if not r['public_candidate']]
    assert len(rows)>100
    for row in rows:
        path=re.sub(r'\{[^}]+\}','1',row['path'])
        response=client.request(row['method'],path,json={})
        assert response.status_code in (401,404), (row['method'],row['path'],response.status_code)
        assert not any(secret in response.text for secret in ('pin_hash','password_hash','token_hash','delivery_street'))


def test_financial_documents_notifications_payouts_and_sessions_under_rls(pg_api):
    client,parameters=pg_api
    seller,_=register(client,'rolnik');other,_=register(client,'rolnik');buyer,_=register(client,'klient')
    admin,uid=register(client,'klient')
    with inspection_connect(**parameters) as con:con.execute("UPDATE users SET role='admin' WHERE id=%s",(uid,))
    response=client.put('/farmers/me/profile',headers=seller,json={'farm_name':'RLS farm','city':'Radom','description':'Test'})
    assert response.status_code==200,response.text
    point=client.post('/pickup-points',headers=seller,json={'name':'RLS point','city':'Radom','street':'Public pickup 1','opening_hours':'8-16'})
    assert point.status_code==201,point.text
    pid=product(client,seller)
    order=client.post('/orders',headers=buyer,json={'product_id':pid,'quantity':1,'fulfillment':'odbior','pickup_point_id':point.json()['id']})
    assert order.status_code==201,order.text
    oid=order.json()['id']
    commission=client.post('/accounting/commission-drafts',headers=seller,json={'order_id':oid,'rate_basis_points':500})
    assert commission.status_code==201,commission.text
    assert client.post('/accounting/commission-drafts',headers=other,json={'order_id':oid,'rate_basis_points':500}).status_code==404
    draft=client.post('/accounting/invoice-drafts',headers=seller,json={'commission_draft_id':commission.json()['id'],'seller_name':'RLS platform','seller_nip':'1234567890','buyer_name':'RLS farmer'})
    assert draft.status_code==201,draft.text
    did=draft.json()['id']
    correction=client.post('/accounting/correction-requests',headers=seller,json={'invoice_draft_id':did,'reason':'Wniosek testowy RLS','requested_net_grosze':17})
    assert correction.status_code==201,correction.text
    for path in ('/accounting/commission-drafts/me','/accounting/invoice-drafts/me','/accounting/correction-requests/me','/accounting/audit/me',f'/accounting/export-preview/{did}'):
        assert client.get(path,headers=seller).status_code==200,path
    job=client.post(f'/accounting/export-jobs/{did}',headers=seller)
    assert job.status_code==201,job.text
    jid=job.json()['id']
    assert client.post(f'/accounting/export-jobs/{did}',headers=other).status_code==404
    for suffix in ('diagnostics','validation-history','review-status'):
        response=client.get(f'/accounting/export-jobs/{jid}/{suffix}',headers=seller)
        assert response.status_code==200,response.text
        assert client.get(f'/accounting/export-jobs/{jid}/{suffix}',headers=other).status_code==404
    validation=client.post(f'/accounting/export-jobs/{jid}/validate',headers=seller)
    assert validation.status_code==200,validation.text
    assert client.post(f'/accounting/export-jobs/{jid}/acknowledge-validation',headers=seller).status_code==200
    for actor in (seller,buyer):
        record=client.get(f'/orders/{oid}/purchase-record',headers=actor)
        assert record.status_code==200,record.text
        notifications=client.get('/notifications/me',headers=actor)
        assert notifications.status_code==200,notifications.text
        assert client.get('/notifications/me/unread-count',headers=actor).status_code==200
    paid=client.post(f'/test/payments/{oid}/events',headers=buyer,json={'event_id':uuid4().hex,'event_type':'payment_success_test'})
    assert paid.status_code==200,paid.text
    assert client.post(f'/test/orders/{oid}/ready',headers=seller).status_code==200
    confirmed=client.post(f'/orders/{oid}/confirm',headers=seller,json={'pin':order.json()['pin_test_only'],'checked_goods':True})
    assert confirmed.status_code==200 and confirmed.json()['confirmed'],confirmed.text
    completed=client.post(f'/test/payments/{oid}/events',headers=seller,json={'event_id':uuid4().hex,'event_type':'order_completed_test'})
    assert completed.status_code==200,completed.text
    report=client.get('/test/farmers/me/payout-report',headers=seller)
    assert report.status_code==200,report.text
    date=report.json()['next_weekly_payout_date']
    plan=client.post('/test/farmers/me/payout-plans',headers=seller)
    assert plan.status_code==200,plan.text
    for suffix in ('','/reconciliation'):
        r=client.get('/test/farmers/me/payout-plans/'+date+suffix,headers=seller)
        assert r.status_code==200,r.text
    reserve=client.post('/test/farmers/me/payout-plans/'+date+'/reserve',headers=seller)
    assert reserve.status_code==200,reserve.text
    assert client.get('/test/farmers/me/payout-plans/'+date+'/reservation-review',headers=seller).status_code==200
    cancel=client.post('/test/farmers/me/payout-plans/'+date+'/cancel-reservation',headers=seller)
    assert cancel.status_code==200,cancel.text
    assert client.post('/test/farmers/me/payout-reservations/reconcile-all',headers=seller).status_code==200
    for path in ('/admin/orders/purchase-record-audit','/admin/shipments/overview','/admin/shipments/reconciliation','/admin/farmers/compliance-queue'):
        r=client.get(path,headers=admin);assert r.status_code==200,r.text
        assert client.get(path,headers=buyer).status_code==403
    sessions=client.get('/auth/sessions',headers=buyer);assert sessions.status_code==200
    assert client.post('/auth/logout-others',headers=buyer).status_code==200
    assert client.post('/auth/logout',headers=buyer).status_code==200
    assert client.get('/auth/me',headers=buyer).status_code==401



def test_weekly_job_uses_restricted_rls_connection_without_http_actor(pg_api):
    from backend.pg_adapter import postgres_db
    from backend.rls_gateway import database_context
    from backend.weekly_job import execute
    from datetime import datetime
    from zoneinfo import ZoneInfo
    from psycopg.conninfo import make_conninfo
    _,parameters=pg_api
    now=datetime(2026,11,16,8,0,tzinfo=ZoneInfo('Europe/Warsaw'))
    with database_context('maintenance'):
        with postgres_db(make_conninfo(**parameters)) as con:
            first=execute(con,now=now,enabled=True)
        with postgres_db(make_conninfo(**parameters)) as con:
            second=execute(con,now=now,enabled=True)
    assert first['transfer_executed'] is False and second['transfer_executed'] is False
    assert second['already_prepared'] is True



def test_extended_endpoint_coverage(pg_api,pg_photo_api,pg_seller_api,pg_address_delivery_api,pg_units_api):
    from datetime import datetime,timezone
    client,parameters=pg_api
    password='RLS-coverage-password-2026'
    seller,seller_id=register(client,'rolnik');buyer,_=register(client,'klient',password=password)
    courier,courier_id=register(client,'dostawca');admin,admin_id=register(client,'klient')
    with inspection_connect(**parameters) as con:con.execute("UPDATE users SET role='admin' WHERE id=%s",(admin_id,))
    def ok(method,path,headers=None,**kw):
        r=client.request(method,path,headers=headers,**kw)
        assert 200<=r.status_code<300,(method,path,r.status_code,r.text)
        return r
    for path in ('/','/products','/product-units','/pickup-point-dates/config','/sellers/config','/user-photos/config','/address-delivery/config','/auth/email-verification/options','/marketplace/accounting-policy'):
        ok('GET',path)
    ok('PUT','/farmers/me/profile',seller,json={'farm_name':'RLS coverage farm','city':'Radom','description':'Test'})
    ok('GET','/farmers/me/profile',seller)
    point=ok('POST','/pickup-points',seller,json={'name':'Point','city':'Radom','street':'Public point 1','opening_hours':'8-16'}).json()['id']
    ok('GET',f'/farmers/{seller_id}/pickup-points')
    pid=product(client,seller,stock=20)
    ok('POST','/cart/quote',buyer,json={'items':[{'product_id':pid,'quantity':1}],'fulfillment':'dostawa'})
    ok('PUT','/cart/items',buyer,json={'product_id':pid,'quantity':1});ok('GET','/cart/items',buyer)
    ok('DELETE',f'/cart/items/{pid}',buyer);ok('DELETE','/cart/items',buyer)
    body={'fulfillment':'dostawa','delivery_city':'Radom','delivery_street':'Private delivery 1','delivery_postal_code':'26-600'}
    def shipment():
        ok('PUT','/cart/items',buyer,json={'product_id':pid,'quantity':1})
        return ok('POST','/cart/checkout-test',buyer,json=body).json()
    first=shipment();sid=first['shipment_id']
    for path,actor in [('/shipments/mine',buyer),('/shipments/farmer/mine',seller),
                       (f'/shipments/{sid}/details',buyer),(f'/shipments/{sid}/financial-history-test',buyer),
                       (f'/shipments/{sid}/purchase-record',seller),(f'/admin/shipments/{sid}/audit',admin)]:ok('GET',path,actor)
    ok('POST',f'/shipments/{sid}/recover-pin-test',buyer,json={'password':password})
    ok('POST',f'/shipments/{sid}/cancel-test',buyer)
    second=shipment()
    for order in second['orders']:ok('POST',f"/test/payments/{order['id']}/events",buyer,json={'event_id':uuid4().hex,'event_type':'payment_success_test'})
    ok('POST',f"/shipments/{second['shipment_id']}/cancel-paid-test",buyer)
    request_key=uuid4().hex
    direct=ok('POST','/orders',{**buyer,'Idempotency-Key':request_key},json={**body,'product_id':pid,'quantity':1}).json()
    oid=direct['id'];ok('GET','/orders/idempotency-status/'+request_key,buyer)
    ok('POST',f'/orders/{oid}/assign-courier-test',seller,json={'courier_id':courier_id})
    ok('POST',f'/test/payments/{oid}/events',buyer,json={'event_id':uuid4().hex,'event_type':'payment_success_test'})
    ok('POST',f'/orders/{oid}/dispatch-test',seller)
    for path,actor in [('/couriers/me/orders',courier),('/couriers/me/shipments',courier),
                       (f'/orders/{oid}/events',seller),(f'/orders/{oid}/location',buyer),(f'/orders/{oid}/location',courier),
                       (f'/marketplace/orders/{oid}/settlement-preview',seller),('/accounting/export-jobs/me',seller)]:ok('GET',path,actor)
    notices=ok('GET','/notifications/me',buyer).json()
    assert isinstance(notices,list) and notices
    ok('POST',f"/notifications/{notices[0]['id']}/read",buyer)
    month=datetime.now(timezone.utc).strftime('%Y-%m')
    ok('GET',f'/test/admin/finance/monthly/{month}',admin)
    ok('GET',f'/test/admin/finance/monthly/{month}/export.csv',admin)
    ok('POST','/test/admin/finance/reconcile',admin,json=[])
    scheduler=client.post('/test/admin/payout-schedule/run',headers=admin)
    assert scheduler.status_code==(200 if datetime.now(timezone.utc).weekday()==0 else 409),scheduler.text
    photos,_=pg_photo_api
    photo_seller,_=register(photos,'rolnik')
    from tests.test_user_photos import picture
    import base64
    image=photos.post('/products/with-photo',headers=photo_seller,json={'name':'With photo','price_grosze':100,'delivery_grosze':50,'stock':1,'photo_base64':base64.b64encode(picture()).decode()})
    assert image.status_code==201,image.text
    assert photos.get('/user-photos/mine',headers=photo_seller).status_code==200
    sellers,_=pg_seller_api
    login_owner,_=register(sellers,'rolnik')
    assert sellers.put('/sellers/me/login',headers=login_owner,json={'login':'rls'+uuid4().hex[:12]}).status_code==200
    assert sellers.get('/sellers/me/login',headers=login_owner).status_code==200
    delivery,_=pg_address_delivery_api
    window_owner,window_farmer=register(delivery,'rolnik')
    window=delivery.post('/address-delivery/windows',headers=window_owner,json={'city':'Radom','postal_code':'26-600','weekday':0,'from_time':'10:00','to_time':'16:00'})
    assert window.status_code==200,window.text
    assert delivery.get('/address-delivery/windows/mine',headers=window_owner).status_code==200
    assert delivery.get(f'/farmers/{window_farmer}/delivery-windows').status_code==200
    changed=delivery.patch('/address-delivery/windows/'+window.json()['id'],headers=window_owner,json={'active':False})
    assert changed.status_code==200,changed.text
    units,_=pg_units_api
    unit_owner,_=register(units,'rolnik');unit_buyer,_=register(units,'klient')
    unit_pid=product(units,unit_owner)
    quote=units.post('/cart/quote-quantities-test',headers=unit_buyer,json={'items':[{'product_id':unit_pid,'quantity_text':'1'}],'fulfillment':'odbior'})
    assert quote.status_code==200,quote.text

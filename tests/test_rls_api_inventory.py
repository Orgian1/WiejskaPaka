"""Additional HTTP coverage on the same restricted RLS API used by native gates."""
import json
import os
from pathlib import Path
import re
from uuid import uuid4
import pytest
from tests.test_postgres_full_api_optin import pg_api,register,product,inspection_connect

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

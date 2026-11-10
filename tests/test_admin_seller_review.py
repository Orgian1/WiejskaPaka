"""Admin queue is private; a decision from a stale view must never overwrite."""
from concurrent.futures import ThreadPoolExecutor
import sqlite3
from uuid import uuid4
import pytest
from backend.seller_compliance import seller_review_queue, acknowledge_seller_rules, review_seller_account, RULES_VERSION
from tests.test_seller_profile_reminder import con
from tests.test_purchase_record_http_restart import server,account


def test_queue_projection_filter_and_stale_revision(con):
    acknowledge_seller_rules(con,1,RULES_VERSION)
    acknowledge_seller_rules(con,4,RULES_VERSION)
    first=seller_review_queue(con,'pending',1,0)
    assert first['total']==2 and first['has_more'] and first['profiles'][0]['farmer_id']==1
    assert seller_review_queue(con,'pending',1,1)['profiles'][0]['farmer_id']==4
    profile=first['profiles'][0]
    expected={key:profile[key] for key in ('rules_version','review_status','reviewed_at')}
    review_seller_account(con,1,2,'approved','Fikcyjny przegląd',expected=expected)
    with pytest.raises(ValueError):review_seller_account(con,1,2,'rejected','Nieaktualny widok',expected=expected)
    assert seller_review_queue(con,'approved')['profiles'][0]['farmer_id']==1
    assert set(profile)=={'farmer_id','rules_version','acknowledged_at','review_status','reviewed_at'}
    assert con.execute("SELECT COUNT(*) FROM seller_compliance_events WHERE event_type LIKE 'review_%'").fetchone()[0]==1


@pytest.mark.parametrize('args',[('wrong',20,0),(None,0,0),(None,51,0),(None,20,-1),(None,20,10001),(None,True,0)])
def test_bad_queue_filters_and_limits_rejected(con,args):
    with pytest.raises(ValueError):seller_review_queue(con,*args)


def create_admin(client,promote):
    """Only tests provision a role directly in their disposable database."""
    body={'email':uuid4().hex+'@example.invalid','password':'Private-admin-test-123!','role':'klient'}
    response=client.post('/auth/register',json=body);assert response.status_code==201
    promote(response.json()['id'])
    response=client.post('/auth/login',json=body);assert response.status_code==200
    return {'Authorization':'Bearer '+response.json()['access_token']},body


def exercise_admin_review(client,admin):
    farmer=account(client,'rolnik');buyer=account(client,'klient')
    fid=client.get('/auth/me',headers=farmer).json()['id']
    queue='/admin/farmers/compliance-queue'
    assert client.get(queue).status_code==401
    for headers in (farmer,buyer):assert client.get(queue,headers=headers).status_code==403
    assert client.get(queue+'?limit=51',headers=admin).status_code==422
    assert client.get(queue+'?status=unknown',headers=admin).status_code==422
    assert client.post('/farmers/me/compliance/acknowledge',headers=farmer,json={'rules_version':RULES_VERSION,'accepted':True}).status_code==200
    response=client.get(queue+'?status=pending&limit=50',headers=admin);assert response.status_code==200,response.text
    profile=next(row for row in response.json()['profiles'] if row['farmer_id']==fid)
    assert set(profile)=={'farmer_id','rules_version','acknowledged_at','review_status','reviewed_at'}
    payload={'decision':'approved','reason':'Wyłącznie testowa decyzja',
        'expected_rules_version':profile['rules_version'],'expected_review_status':profile['review_status'],'expected_reviewed_at':profile['reviewed_at']}
    url=f'/admin/farmers/{fid}/compliance/review'
    assert client.post(url,headers=farmer,json=payload).status_code==403
    incomplete={**payload};incomplete.pop('expected_reviewed_at')
    assert client.post(url,headers=admin,json=incomplete).status_code==409
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(lambda decision:client.post(url,headers=admin,json={**payload,'decision':decision}),('approved','needs_information')))
    assert sorted(r.status_code for r in results)==[200,409]
    result=client.get('/farmers/me/compliance',headers=farmer).json()
    assert result['review_status'] in ('approved','needs_information')
    assert result['can_receive_real_payouts'] is False
    assert client.post(url,headers=admin,json=payload).status_code==409
    return fid


def test_real_http_queue_concurrent_decisions_and_role_isolation(tmp_path):
    database=tmp_path/'admin.sqlite3'
    with server(database) as client:
        def promote(uid):
            with sqlite3.connect(database) as con:con.execute("UPDATE users SET role='admin' WHERE id=?",(uid,))
        admin,_=create_admin(client,promote)
        fid=exercise_admin_review(client,admin)
    with sqlite3.connect(database) as con:
        assert con.execute("SELECT COUNT(*) FROM seller_compliance_events WHERE farmer_id=? AND event_type LIKE 'review_%'",(fid,)).fetchone()[0]==1


def test_review_timestamp_prevents_overwrite_after_status_returns_to_previous_value(con,monkeypatch):
    import backend.seller_compliance as compliance
    from datetime import datetime,timezone
    class FrozenClock(datetime):
        @classmethod
        def now(cls,tz=None):return cls(2026,1,1,tzinfo=timezone.utc)
    monkeypatch.setattr(compliance,'datetime',FrozenClock)
    acknowledge_seller_rules(con,1,RULES_VERSION)
    review_seller_account(con,1,2,'approved','Decyzja pierwsza')
    old=seller_review_queue(con,'approved')['profiles'][0]
    expected={key:old[key] for key in ('rules_version','review_status','reviewed_at')}
    review_seller_account(con,1,2,'needs_information','Do wyjaśnienia')
    review_seller_account(con,1,2,'approved','Ponowne zatwierdzenie')
    with pytest.raises(ValueError):
        review_seller_account(con,1,2,'rejected','Stary widok zatwierdzenia',expected=expected)
    assert seller_review_queue(con,'approved')['profiles'][0]['reviewed_at']!=old['reviewed_at']

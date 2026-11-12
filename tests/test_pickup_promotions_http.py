"""Real HTTP + durable SQLite: promotion limits and three atomic point credits."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sqlite3
from uuid import uuid4
import pytest
from tests.test_sample_demo import prepare_sample
from tests.test_purchase_record_http_restart import server
from tests.test_owner_finalization import login

FUTURE='2099-12-31'
POINT={'name':'Punkt promocyjny','city':'Legnica','street':'Testowa 4','opening_hours':'9-16'}


def headers(client,sample):
    return {role:login(client,creds) for role,creds in sample['credentials'].items()}


def create(client,admin,code='TRZYPUNKTY',**changes):
    return client.post('/admin/pickup-promotions',headers=admin,json={'code':code,'expires_on':FUTURE,'max_redemptions':10,**changes})


def seller(client):
    credentials={'email':uuid4().hex+'@example.invalid','password':'Synthetic-Promotion-Password-123!','role':'rolnik'}
    assert client.post('/auth/register',json=credentials).status_code==201
    return login(client,{k:v for k,v in credentials.items() if k!='role'})


def test_three_credits_are_idempotent_private_and_persistent(tmp_path):
    sample=prepare_sample(tmp_path/'promo');database=Path(sample['database'])
    with server(database) as client:
        h=headers(client,sample)
        assert client.get('/admin/pickup-promotions').status_code==401
        assert create(client,h['rolnik']).status_code==403
        assert create(client,h['admin']).status_code==201
        assert create(client,h['admin']).status_code==409
        assert client.post('/farmers/me/pickup-promotions/redeem',headers=h['klient'],json={'code':'TRZYPUNKTY'}).status_code==403
        for status in (201,200):
            response=client.post('/farmers/me/pickup-promotions/redeem',headers=h['rolnik'],json={'code':'trzypunkty'})
            assert response.status_code==status and response.json()['remaining']==3
        for i in range(4):
            response=client.post('/pickup-points',headers=h['rolnik'],json={**POINT,'name':f'Punkt {i}'})
            assert response.status_code==201
            assert response.json()['promotion']==({'free_until':FUTURE,'charges_executed':False} if i<3 else None)
        own=client.get('/farmers/me/pickup-promotions',headers=h['rolnik'])
        assert own.headers['cache-control']=='no-store' and own.json()['available_points']==0
        other=seller(client)
        assert client.get('/farmers/me/pickup-promotions',headers=other).json()=={'items':[],'available_points':0}
        listed=client.get('/farmers/me/pickup-points',headers=h['rolnik']).json()
        assert sum(bool(p['promotion']) for p in listed)==3
        replay=client.post('/farmers/me/pickup-promotions/redeem',headers=h['rolnik'],json={'code':'TRZYPUNKTY'})
        assert replay.status_code==200 and replay.json()['remaining']==0
    with server(database) as client:
        h=headers(client,sample)
        assert client.get('/farmers/me/pickup-promotions',headers=h['rolnik']).json()['available_points']==0
        assert client.get('/admin/pickup-promotions',headers=h['admin']).json()['items'][0]['redemption_count']==1
        assert sum(bool(p['promotion']) for p in client.get('/farmers/me/pickup-points',headers=h['rolnik']).json())==3


def test_concurrent_redeem_and_point_creation_never_exceed_limits(tmp_path):
    sample=prepare_sample(tmp_path/'races')
    with server(Path(sample['database'])) as client:
        h=headers(client,sample);assert create(client,h['admin'],max_redemptions=1).status_code==201
        def redeem(_):return client.post('/farmers/me/pickup-promotions/redeem',headers=h['rolnik'],json={'code':'TRZYPUNKTY'})
        with ThreadPoolExecutor(max_workers=5) as pool:responses=list(pool.map(redeem,range(5)))
        assert sorted(r.status_code for r in responses)==[200,200,200,200,201]
        with ThreadPoolExecutor(max_workers=6) as pool:points=list(pool.map(lambda i:client.post('/pickup-points',headers=h['rolnik'],json={**POINT,'name':f'Równoległy {i}'}),range(6)))
        assert all(r.status_code==201 for r in points)
        assert sum(r.json()['promotion'] is not None for r in points)==3
        assert client.get('/farmers/me/pickup-promotions',headers=h['rolnik']).json()['available_points']==0
        assert client.get('/admin/pickup-promotions',headers=h['admin']).json()['items'][0]['redemption_count']==1


def test_global_code_limit_serializes_different_accounts(tmp_path):
    sample=prepare_sample(tmp_path/'global')
    with server(Path(sample['database'])) as client:
        h=headers(client,sample);assert create(client,h['admin'],max_redemptions=1).status_code==201
        actors=[h['rolnik'],seller(client),seller(client),seller(client)]
        with ThreadPoolExecutor(max_workers=4) as pool:
            results=list(pool.map(lambda actor:client.post('/farmers/me/pickup-promotions/redeem',headers=actor,json={'code':'TRZYPUNKTY'}),actors))
        assert sorted(r.status_code for r in results)==[201,409,409,409]


def test_expiry_disable_and_admin_updates_preserve_already_granted_terms(tmp_path):
    sample=prepare_sample(tmp_path/'expiry')
    with server(Path(sample['database'])) as client:
        h=headers(client,sample)
        assert create(client,h['admin'],code='EXPIRED',expires_on='2000-01-01').status_code==201
        assert client.post('/farmers/me/pickup-promotions/redeem',headers=h['rolnik'],json={'code':'EXPIRED'}).status_code==409
        assert create(client,h['admin'],code='DISABLED',active=False).status_code==201
        assert client.post('/farmers/me/pickup-promotions/redeem',headers=h['rolnik'],json={'code':'DISABLED'}).status_code==409
        assert create(client,h['admin']).status_code==201
        assert client.post('/farmers/me/pickup-promotions/redeem',headers=h['rolnik'],json={'code':'TRZYPUNKTY'}).status_code==201
        settings={'expires_on':'2000-01-01','max_redemptions':1,'active':False}
        assert client.put('/admin/pickup-promotions/TRZYPUNKTY',headers=h['admin'],json=settings).status_code==200
        assert client.post('/farmers/me/pickup-promotions/redeem',headers=seller(client),json={'code':'TRZYPUNKTY'}).status_code==409
        assert client.post('/pickup-points',headers=h['rolnik'],json=POINT).json()['promotion']['free_until']==FUTURE
        assert client.put('/admin/pickup-promotions/TRZYPUNKTY',headers=h['admin'],json={**settings,'max_redemptions':0}).status_code==422
        assert client.put('/admin/pickup-promotions/!!!',headers=h['admin'],json=settings).status_code==422


def test_failed_point_transaction_does_not_consume_credit(tmp_path):
    sample=prepare_sample(tmp_path/'rollback');database=Path(sample['database'])
    with server(database) as client:
        h=headers(client,sample);assert create(client,h['admin']).status_code==201
        assert client.post('/farmers/me/pickup-promotions/redeem',headers=h['rolnik'],json={'code':'TRZYPUNKTY'}).status_code==201
        before=len(client.get('/farmers/me/pickup-points',headers=h['rolnik']).json())
        with sqlite3.connect(database) as con:
            con.execute("CREATE TRIGGER reject_test_promo_point BEFORE INSERT ON pickup_promo_points BEGIN SELECT RAISE(ABORT,'Synthetic rollback'); END")
        assert client.post('/pickup-points',headers={**h['rolnik'],'Connection':'close'},json=POINT).status_code==500
        assert len(client.get('/farmers/me/pickup-points',headers=h['rolnik']).json())==before
        assert client.get('/farmers/me/pickup-promotions',headers=h['rolnik']).json()['available_points']==3


@pytest.mark.parametrize('changes',[{'code':'BAD!'}, {'max_redemptions':True},{'max_redemptions':0},{'expires_on':'2101-01-01'},{'extra':'untrusted'}])
def test_admin_payload_validation(tmp_path,changes):
    sample=prepare_sample(tmp_path/'validation')
    with server(Path(sample['database'])) as client:
        admin=login(client,sample['credentials']['admin'])
        assert create(client,admin,**changes).status_code==422


def test_expiry_is_inclusive_and_expired_grants_cannot_fund_a_new_point():
    from datetime import date
    from backend.pickup_promotions import SCHEMA,consume_for_point,grant_reply
    con=sqlite3.connect(':memory:');con.row_factory=sqlite3.Row
    con.executescript('CREATE TABLE users(id INTEGER PRIMARY KEY); CREATE TABLE pickup_points(id INTEGER PRIMARY KEY); INSERT INTO users VALUES(1); INSERT INTO pickup_points VALUES(1); INSERT INTO pickup_points VALUES(2);'+SCHEMA)
    con.execute("INSERT INTO pickup_promo_codes VALUES('BOUNDARY','2026-12-31',1,1,1)")
    con.execute("INSERT INTO pickup_promo_grants VALUES('grant',1,'BOUNDARY','2026-12-31',3)")
    assert consume_for_point(con,1,1,today=date(2026,12,31))['free_until']=='2026-12-31'
    assert consume_for_point(con,1,2,today=date(2027,1,1)) is None
    row=con.execute('SELECT * FROM pickup_promo_grants').fetchone()
    assert row['remaining']==2 and grant_reply(row,today=date(2027,1,1))['remaining']==0
    assert con.execute('SELECT count(*) FROM pickup_promo_points').fetchone()[0]==1
    con.close()


def test_admin_cannot_reduce_limit_below_existing_redemptions(tmp_path):
    sample=prepare_sample(tmp_path/'reduced-limit')
    with server(Path(sample['database'])) as client:
        h=headers(client,sample);assert create(client,h['admin']).status_code==201
        for actor in (h['rolnik'],seller(client)):
            assert client.post('/farmers/me/pickup-promotions/redeem',headers=actor,json={'code':'TRZYPUNKTY'}).status_code==201
        response=client.put('/admin/pickup-promotions/TRZYPUNKTY',headers=h['admin'],json={'expires_on':FUTURE,'max_redemptions':1,'active':True})
        assert response.status_code==409
        assert client.get('/admin/pickup-promotions',headers=h['admin']).json()['items'][0]['redemption_count']==2

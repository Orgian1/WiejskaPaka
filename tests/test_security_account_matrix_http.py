"""Real API denial matrix: identity always comes from the bearer session."""
import os
os.environ['WP_ENV'] = 'test'
os.environ['WP_ENABLE_WALLET_PREVIEW'] = '1'
import uuid
import pytest
from fastapi.testclient import TestClient
from backend import app as api

PASSWORD='isolated-security-account-password-2026'

@pytest.fixture(scope='module')
def scenario():
    with TestClient(api.app) as client:
        actors={}
        for label,role in [('buyer','klient'),('other','klient'),('seller','rolnik'),('outsider','rolnik'),('courier','dostawca'),('admin','klient')]:
            email=f'{uuid.uuid4().hex}@example.test'
            registered=client.post('/auth/register',json={'email':email,'password':PASSWORD,'role':role})
            assert registered.status_code==201,registered.text
            uid=registered.json()['id']
            if label=='admin':
                # Privileged test fixture, never an API available to the client.
                with api.db() as con:con.execute("UPDATE users SET role='admin' WHERE id=?",(uid,))
            token=client.post('/auth/login',json={'email':email,'password':PASSWORD}).json()['access_token']
            actors[label]={'Authorization':f'Bearer {token}'}
        product=client.post('/products',headers=actors['seller'],json={'name':'Security matrix','price_grosze':100,'delivery_grosze':50,'stock':10})
        assert product.status_code==201
        order=client.post('/orders',headers=actors['buyer'],json={'product_id':product.json()['id'],'quantity':1,'fulfillment':'dostawa','delivery_city':'Private city','delivery_street':'Private street 42','delivery_postal_code':'00-001'})
        assert order.status_code==201,order.text
        yield client,actors,order.json()['id']

@pytest.mark.parametrize('actor',['other','outsider','courier','admin'])
def test_private_purchase_and_address_cannot_be_claimed(scenario,actor):
    client,actors,oid=scenario
    for suffix in ('location','purchase-record'):
        response=client.get(f'/orders/{oid}/{suffix}',headers=actors[actor])
        assert response.status_code in (403,404)
        assert 'Private street' not in response.text
        assert 'pin_hash' not in response.text

@pytest.mark.parametrize('actor',['buyer','other','seller','outsider','courier'])
def test_admin_views_are_not_ordinary_account_permissions(scenario,actor):
    client,actors,_=scenario
    for path in ('/admin/shipments/overview','/admin/orders/purchase-record-audit','/admin/wallet/withdrawals-test','/admin/farmers/compliance-queue'):
        assert client.get(path,headers=actors[actor]).status_code==403


def test_admin_registration_and_forged_identity_headers_fail(scenario):
    client,actors,oid=scenario
    assert client.post('/auth/register',json={'email':'forged-admin@example.test','password':PASSWORD,'role':'admin'}).status_code==422
    headers={**actors['other'],'X-User-Id':'1','X-Role':'admin','X-Actor-Id':'1'}
    assert client.get(f'/orders/{oid}/location',headers=headers).status_code==403
    assert client.get('/admin/shipments/overview',headers=headers).status_code==403
    assert client.get('/auth/me',headers={'Authorization':'Bearer invented-session'}).status_code==401


def test_unauthorized_writes_leave_order_unchanged(scenario):
    client,actors,oid=scenario
    with api.db() as con:before=dict(con.execute('SELECT * FROM orders WHERE id=?',(oid,)).fetchone())
    for actor in ('other','outsider','courier'):
        assert client.post(f'/orders/{oid}/cancel-test',headers=actors[actor]).status_code in (403,404)
        assert client.post(f'/orders/{oid}/confirm',headers=actors[actor],json={'pin':'000000','checked_goods':True}).status_code in (403,404)
    with api.db() as con:after=dict(con.execute('SELECT * FROM orders WHERE id=?',(oid,)).fetchone())
    assert after==before


def test_wallet_mass_assignment_and_role_limits(scenario):
    client,actors,_=scenario
    assert client.post('/wallet/topups',headers=actors['buyer'],json={'amount_grosze':100,'request_key':uuid.uuid4().hex,'user_id':2}).status_code==422
    for actor in ('courier','admin'):
        assert client.get('/wallet',headers=actors[actor]).status_code==403
    for actor in ('buyer','other','seller'):
        response=client.get('/wallet',headers=actors[actor])
        assert response.status_code==200,response.text
        assert response.json()['available_grosze']==0
        for secret in ('pin_hash','password_hash','token_hash','Private street'):
            assert secret not in response.text

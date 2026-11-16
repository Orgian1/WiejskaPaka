"""Real HTTP atomic wallet ads, campaign administration and wallet independence."""
import base64
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from datetime import datetime, timedelta, timezone
from io import BytesIO
import sqlite3
from uuid import uuid4
import pytest
from PIL import Image
from tests.test_purchase_record_http_restart import server
from tests.test_postgres_full_api_optin import register

DEVICE_PASSWORD='Synthetic-wallet-ads-two-device-password-2026!'


def campaign(**overrides):
    data=BytesIO();Image.new('RGB',(900,400),'green').save(data,'PNG')
    now=datetime.now(timezone.utc).replace(microsecond=0)
    return dict(advertiser='Gospodarstwo testowe',url='https://example.org/oferta',
        image_base64=base64.b64encode(data.getvalue()).decode(),
        starts_at=(now-timedelta(hours=1)).isoformat(),ends_at=(now+timedelta(days=1)).isoformat(),
        enabled=True,sort_order=0,**overrides)


def claim(client,headers,key=None):
    return client.post('/wallet/ads/claim',headers=headers,json={'request_key':key or uuid4().hex})


def exercise(client,admin,buyer,seller,other,expire):
    body=campaign();body['url']='HTTPS://example.org/oferta'
    assert claim(client,buyer).json()=={'ad':None}
    for headers in (buyer,seller,other):
        assert client.get('/admin/wallet-ads',headers=headers).status_code==403
        assert client.post('/admin/wallet-ads',headers=headers,json=body).status_code==403
        assert client.put('/admin/wallet-ads/other',headers=headers,json=body).status_code==403
        assert client.delete('/admin/wallet-ads/other',headers=headers).status_code==403
    assert claim(client,{}).status_code==401
    first=client.post('/admin/wallet-ads',headers=admin,json=body)
    assert first.status_code==201,first.text
    aid=first.json()['id'];body['advertiser']='Druga reklama';body['sort_order']=1
    second=client.post('/admin/wallet-ads',headers=admin,json=body);assert second.status_code==201
    bid=second.json()['id']
    before=client.get('/wallet',headers=buyer).json()
    key=uuid4().hex
    # Distinct live sessions and entry keys model two independently logged-in devices.
    email=client.get('/auth/me',headers=buyer).json()['email']
    login=client.post('/auth/login',json={'email':email,'password':DEVICE_PASSWORD})
    assert login.status_code==200,login.text
    second_device={'Authorization':'Bearer '+login.json()['access_token']}
    assert second_device!=buyer
    with ThreadPoolExecutor(2) as pool:
        responses=list(pool.map(lambda headers:claim(client,headers),[buyer,second_device]))
    assert all(r.status_code==200 for r in responses),[r.text for r in responses]
    ads=[r.json()['ad'] for r in responses if r.json()['ad']]
    assert len(ads)==1
    ad=ads[0];assert ad['id']==aid and ad['duration_seconds']==5
    assert ad['url']=='https://example.org/oferta'
    assert ad['image'].startswith('data:image/jpeg;base64,')
    assert claim(client,buyer,key).json()=={'ad':None}
    assert claim(client,buyer,key).json()=={'ad':None}
    assert client.get('/wallet',headers=buyer).json()==before
    iid=ad['impression_id']
    path=f'/wallet/ads/impressions/{iid}/click'
    assert client.post(path,headers=other).status_code==404
    for _ in range(3):assert client.post(path,headers=buyer).status_code==200
    assert claim(client,seller).json()['ad']['id']==aid
    assert claim(client,other).json()['ad']['id']==aid
    rows=client.get('/admin/wallet-ads',headers=admin).json()['items']
    assert rows[0]['impressions']==3 and rows[0]['clicks']==1
    assert not any(word in str(rows) for word in ('user_id','token_hash','pin_hash','email'))
    expire()
    next_ad=claim(client,buyer,key).json()['ad'];assert next_ad['id']==bid
    expire()
    assert claim(client,buyer,key).json()=={'ad':None} # same entry never counted twice
    body['enabled']=False
    assert client.put('/admin/wallet-ads/'+bid,headers=admin,json=body).status_code==200
    assert client.delete('/admin/wallet-ads/'+aid,headers=admin).status_code==200
    assert claim(client,buyer).json()=={'ad':None}
    assert client.get('/admin/wallet-ads',headers=admin).json()['items'][0]['impressions']==1
    assert client.post('/auth/logout',headers=buyer).status_code==200
    assert claim(client,buyer).status_code==401


def test_wallet_ads_full_http(tmp_path,monkeypatch):
    monkeypatch.setenv('WP_ENABLE_WALLET_PREVIEW','1');path=tmp_path/'ads.sqlite3'
    with server(path) as client:
        buyer,uid=register(client,'klient',password=DEVICE_PASSWORD);seller,_=register(client,'rolnik');other,_=register(client,'klient');admin,aid=register(client,'klient')
        with closing(sqlite3.connect(path)) as con:
            con.execute("UPDATE users SET role='admin' WHERE id=?",(aid,));con.commit()
        def expire():
            with closing(sqlite3.connect(path)) as con:
                con.execute('UPDATE wallet_ad_accounts SET last_shown=last_shown-1801 WHERE user_id=?',(uid,));con.commit()
        exercise(client,admin,buyer,seller,other,expire)


@pytest.mark.parametrize('field,value', [('url','javascript:alert(1)'),('url','data:text/html,bad'),('url','https://user:secret@example.org'),('url','https://example.org\\@evil.org'),('url','https://example.org\n.evil.org'),('image_base64','<svg onload=alert(1)>'),('image_base64',base64.b64encode(b'<svg/>').decode()),('ends_at','2020-01-01T00:00:00Z'),('starts_at','2026-01-01T00:00:00'),('user_id',2),('starts_at','2026-01-01T00:00:00.123Z')])
def test_campaign_validation(tmp_path,field,value):
    path=tmp_path/'invalid.sqlite3'
    with server(path) as client:
        admin,uid=register(client,'klient')
        with closing(sqlite3.connect(path)) as con:
            con.execute("UPDATE users SET role='admin' WHERE id=?",(uid,));con.commit()
        body=campaign();body[field]=value
        assert client.post('/admin/wallet-ads',headers=admin,json=body).status_code==422


def test_ads_schedule_roles_spoofing_and_cap_survives_restart(tmp_path,monkeypatch):
    monkeypatch.setenv('WP_ENABLE_WALLET_PREVIEW','1');path=tmp_path/'restart.sqlite3'
    with server(path) as client:
        buyer,uid=register(client,'klient');courier,_=register(client,'dostawca');admin,aid=register(client,'klient')
        with closing(sqlite3.connect(path)) as con:
            con.execute("UPDATE users SET role='admin' WHERE id=?",(aid,));con.commit()
        assert claim(client,courier).status_code==403
        assert claim(client,admin).status_code==403
        assert client.post('/wallet/ads/claim',headers=buyer,json={'request_key':uuid4().hex,'actor_id':aid}).status_code==422
        body=campaign();body['enabled']=False
        ad=client.post('/admin/wallet-ads',headers=admin,json=body).json()['id']
        assert claim(client,buyer).json()=={'ad':None}
        now=datetime.now(timezone.utc).replace(microsecond=0);body.update(enabled=True,starts_at=(now+timedelta(hours=1)).isoformat(),ends_at=(now+timedelta(hours=2)).isoformat())
        assert client.put('/admin/wallet-ads/'+ad,headers=admin,json=body).status_code==200
        assert claim(client,buyer).json()=={'ad':None}
        body.update(starts_at=(now-timedelta(hours=2)).isoformat(),ends_at=(now-timedelta(hours=1)).isoformat())
        assert client.put('/admin/wallet-ads/'+ad,headers=admin,json=body).status_code==200
        assert claim(client,buyer).json()=={'ad':None}
        body=campaign();assert client.put('/admin/wallet-ads/'+ad,headers=admin,json=body).status_code==200
        assert claim(client,buyer).json()['ad']
    with server(path) as client:
        assert claim(client,buyer).json()=={'ad':None}
        with closing(sqlite3.connect(path)) as con:
            con.execute("UPDATE wallet_ad_accounts SET last_shown=CAST(strftime('%s','now') AS INTEGER)-1790 WHERE user_id=?",(uid,));con.commit()
        assert claim(client,buyer).json()=={'ad':None}


def test_all_ad_routes_require_authentication(tmp_path):
    with server(tmp_path/'anonymous.sqlite3') as client:
        for method,path in [('POST','/wallet/ads/claim'),('POST','/wallet/ads/impressions/unknown/click'),('GET','/admin/wallet-ads'),('POST','/admin/wallet-ads'),('PUT','/admin/wallet-ads/unknown'),('DELETE','/admin/wallet-ads/unknown')]:
            assert client.request(method,path,json={}).status_code==401

"""Route order is private, durable and cannot overwrite another device silently."""
from concurrent.futures import ThreadPoolExecutor
import uuid
import pytest
from fastapi.testclient import TestClient
from backend import app as module


def register(client, role):
    credentials={'email':uuid.uuid4().hex+'@example.invalid','password':'PrivateNavigationPassword2026','role':role}
    result=client.post('/auth/register',json=credentials);assert result.status_code==201
    return {'Authorization':'Bearer '+client.post('/auth/login',json=credentials).json()['access_token']}


def point(client, owner, name):
    response=client.post('/pickup-points',headers=owner,json={'name':name,'city':'Legnica','street':'Testowa 1','opening_hours':'9-16'})
    assert response.status_code==201
    return response.json()['id']


def exercise_navigation(client):
    owner,other,buyer,courier=[register(client,r) for r in ('rolnik','rolnik','klient','dostawca')]
    a,b=point(client,owner,'Pierwszy'),point(client,owner,'Drugi');foreign=point(client,other,'Cudzy')
    url='/farmers/me/navigation'
    assert client.get(url).status_code==401
    for actor in (buyer,courier):
        assert client.get(url,headers=actor).status_code==403
        assert client.put(url,headers=actor,json={'revision':0,'point_ids':[]}).status_code==403
    assert client.get(url,headers=owner).json()=={'revision':0,'point_ids':[a,b]}
    assert client.put(url,headers=owner,json={'revision':0,'point_ids':[foreign]}).status_code==404
    saved=client.put(url,headers=owner,json={'revision':0,'point_ids':[b,a]})
    assert saved.status_code==200 and saved.json()=={'revision':1,'point_ids':[b,a]}
    assert client.get(url,headers=other).json()=={'revision':0,'point_ids':[foreign]}
    assert client.put(url,headers=owner,json={'revision':0,'point_ids':[a,b]}).status_code==409
    c=point(client,owner,'Nowy');assert client.get(url,headers=owner).json()=={'revision':1,'point_ids':[b,a,c]}
    with ThreadPoolExecutor(max_workers=2) as pool:
        replies=list(pool.map(lambda ids:client.put(url,headers=owner,json={'revision':1,'point_ids':ids}),[[a,b,c],[c,b,a]]))
    assert sorted(r.status_code for r in replies)==[200,409]
    final=client.get(url,headers=owner).json();assert final['revision']==2
    return owner,final


def test_private_order_and_competing_devices():
    exercise_navigation(TestClient(module.app))


@pytest.mark.parametrize('ids',[[True],[1,1],[-1],['1'],[1.5],list(range(1,1002))])
def test_invalid_route_cannot_be_saved(ids):
    client=TestClient(module.app);owner=register(client,'rolnik')
    assert client.put('/farmers/me/navigation',headers=owner,json={'revision':0,'point_ids':ids}).status_code==422

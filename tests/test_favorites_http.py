"""Persistent, idempotent favorites scoped to the verified account."""
from pathlib import Path
from tests.test_sample_demo import prepare_sample
from tests.test_purchase_record_http_restart import server
from tests.test_owner_finalization import login


def test_favorites_are_private_idempotent_and_survive_restart(tmp_path):
    sample=prepare_sample(tmp_path/'favorites')
    database=Path(sample['database'])
    with server(database) as client:
        buyer=login(client,sample['credentials']['klient']);seller=login(client,sample['credentials']['rolnik'])
        product=client.get('/products').json()[0]['id']
        assert client.get('/favorites').status_code==401
        assert client.put(f'/favorites/{product}').status_code==401
        assert client.get('/favorites',headers=buyer).json()['items']==[]
        for _ in range(2):assert client.put(f'/favorites/{product}',headers=buyer).json()=={'favorite':True}
        response=client.get('/favorites',headers=buyer)
        assert response.headers['cache-control']=='no-store'
        assert [p['id'] for p in response.json()['items']]==[product]
        assert client.get('/favorites',headers=seller).json()['items']==[]
        assert client.delete(f'/favorites/{product}',headers=seller).status_code==200
        assert len(client.get('/favorites',headers=buyer).json()['items'])==1
        assert client.get('/favorites?limit=101',headers=buyer).status_code==422
        assert client.get('/favorites?offset=-1',headers=buyer).status_code==422
        assert client.put('/favorites/99999999',headers=buyer).status_code==404
    with server(database) as client:
        buyer=login(client,sample['credentials']['klient'])
        assert [p['id'] for p in client.get('/favorites',headers=buyer).json()['items']]==[product]
        for _ in range(2):assert client.delete(f'/favorites/{product}',headers=buyer).json()=={'favorite':False}
        assert client.get('/favorites',headers=buyer).json()['items']==[]


def test_saved_location_is_explicit_private_validated_and_durable(tmp_path):
    sample=prepare_sample(tmp_path/'location');database=Path(sample['database'])
    location={'latitude_e6':52229676,'longitude_e6':21012229}
    with server(database) as client:
        buyer=login(client,sample['credentials']['klient']);seller=login(client,sample['credentials']['rolnik'])
        assert client.put('/account/location',json=location).status_code==401
        assert client.get('/account/location',headers=buyer).json()=={'location':None}
        assert client.put('/account/location',headers=buyer,json={**location,'latitude_e6':True}).status_code==422
        assert client.put('/account/location',headers=buyer,json={**location,'latitude_e6':90000001}).status_code==422
        assert client.put('/account/location',headers=buyer,json=location).status_code==200
        assert client.get('/account/location',headers=seller).json()=={'location':None}
        response=client.get('/account/location',headers=buyer)
        assert response.headers['cache-control']=='no-store' and response.json()=={'location':location}
    with server(database) as client:
        buyer=login(client,sample['credentials']['klient'])
        assert client.get('/account/location',headers=buyer).json()=={'location':location}
        assert client.delete('/account/location',headers=buyer).status_code==200
        assert client.get('/account/location',headers=buyer).json()=={'location':None}

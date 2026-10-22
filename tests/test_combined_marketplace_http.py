"""Real HTTP with optional marketplace features enabled together, including restart."""
from datetime import datetime, timedelta
from io import BytesIO
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest
from PIL import Image
from tests.test_purchase_record_http_restart import server


@pytest.mark.parametrize('decision',['accepted','declined'])
def test_units_photos_seller_search_and_shared_address_delivery(tmp_path,monkeypatch,decision):
    for name in ('PRODUCT_UNITS','USER_PHOTOS','SELLER_SEARCH','ADDRESS_DELIVERY'):
        monkeypatch.setenv('WP_ENABLE_'+name,'1')
    database=tmp_path/'combined.sqlite3'
    day=datetime.now(ZoneInfo('Europe/Warsaw')).date()+timedelta(days=7)
    with server(database) as client:
        actors=[]
        for role in ('rolnik','klient','klient'):
            credentials={'email':uuid4().hex+'@example.invalid','password':'CombinedPrivatePassword2026!','role':role}
            registered=client.post('/auth/register',json=credentials)
            assert registered.status_code==201,registered.text
            token=client.post('/auth/login',json=credentials).json()['access_token']
            actors.append(({'Authorization':'Bearer '+token},registered.json()['id']))
        (farmer,farmer_id),(buyer,_),(outsider,_)=actors
        handle='combined_'+uuid4().hex[:10]
        assert client.put('/sellers/me/login',headers=farmer,json={'login':handle}).status_code==200
        assert client.put('/farmers/me/profile',headers=farmer,json={
            'farm_name':'Wspólne gospodarstwo','city':'Legnica','description':'Dane syntetyczne'}).status_code==200
        found=client.get('/sellers/search',params={'q':'@'+handle}).json()['items']
        assert len(found)==1 and found[0]['farmer_id']==farmer_id
        assert set(found[0])=={'farmer_id','login','farm_name','city'}
        products=[]
        for name,unit,price in [('Pomidory wspólnej paczki','kg',349),('Ogórki w słoiku','sloik',299)]:
            payload={'name':name,'sale_unit':unit,'price_grosze':price,'delivery_grosze':501,'stock':10}
            if unit=='sloik':payload.update(content_amount='0,75',content_unit='l')
            response=client.post('/products',headers=farmer,json=payload)
            assert response.status_code==201,response.text
            products.append(response.json()['id'])
        catalog=client.get('/catalog/search',params={'farmer_id':farmer_id}).json()['items']
        assert {p['sale_unit'] for p in catalog}=={'kg','sloik'}
        assert next(p for p in catalog if p['sale_unit']=='sloik')['package_content']=={'amount_atoms':750,'unit':'l'}
        image=Image.new('RGB',(1800,1200),'green');stream=BytesIO()
        exif=Image.Exif();exif[270]='synthetic private metadata';image.save(stream,'PNG',exif=exif)
        photo_url=f'/user-photos/product/{products[0]}'
        uploaded=client.put(photo_url,headers=farmer,content=stream.getvalue())
        assert uploaded.status_code==200,uploaded.text
        photo=client.get(photo_url)
        assert photo.status_code==200 and 0<len(photo.content)<=1_000_000
        assert photo.headers['content-type']=='image/jpeg'
        assert not Image.open(BytesIO(photo.content)).getexif()
        assert client.put(photo_url,headers=outsider,content=stream.getvalue()).status_code==404
        window=client.post('/address-delivery/windows',headers=farmer,json={
            'city':'Legnica','postal_code':'59-220','weekday':day.weekday(),'from_time':'10:00','to_time':'16:00'})
        assert window.status_code==200,window.text
        for pid,qty in zip(products,(2,1)):
            assert client.put('/cart/items',headers=buyer,json={'product_id':pid,'quantity':qty}).status_code==200
        payload={'farmer_id':farmer_id,'fulfillment':'dostawa','delivery_city':'Legnica',
            'delivery_street':'Testowa 1','delivery_postal_code':'59-220','address_delivery':{
                'window_id':window.json()['id'],'delivery_date':day.isoformat(),
                'available_from':'12:00','available_to':'18:00','phone':'+48 500 100 200'}}
        key='combined-checkout-'+uuid4().hex
        reply=client.post('/cart/checkout-test',headers={**buyer,'Idempotency-Key':key},json=payload)
        assert reply.status_code==201,reply.text
        shipment_id=reply.json()['shipment_id']
        assert reply.json()['delivery_grosze']==501 and reply.json()['total_grosze']==1498
        replay=client.post('/cart/checkout-test',headers={**buyer,'Idempotency-Key':key},json=payload)
        assert replay.status_code==201 and replay.json()['shipment_id']==shipment_id
        orders=client.get('/orders/me',headers=buyer).json()
        assert len(orders)==2
        originals={o['id']:client.get(f"/orders/{o['id']}/purchase-record",headers=buyer).json()['original'] for o in orders}
        assert {r['product']['sale_unit'] for r in originals.values()}=={'kg','sloik'}
        assert sum(r['delivery_grosze'] for r in originals.values())==501
        assert sum(r['total_grosze'] for r in originals.values())==1498
        for headers in (farmer,buyer):
            requests=client.get('/address-delivery/requests/mine',headers=headers)
            assert len(requests.json()['items'])==2
            assert '500100200' not in requests.text and '500 100 200' not in requests.text
        oid=orders[0]['id']
        assert client.post(f'/address-delivery/requests/{oid}/decision',headers=outsider,
                           json={'decision':decision,'revision':0}).status_code==403
    # A real process restart must retain the shared request, units and bounded photo.
    with server(database) as client:
        assert client.get(photo_url).content==photo.content
        response=client.post(f'/address-delivery/requests/{oid}/decision',headers=farmer,
                             json={'decision':decision,'revision':0})
        assert response.status_code==200,response.text
        again=client.post(f'/address-delivery/requests/{oid}/decision',headers=farmer,
                         json={'decision':decision,'revision':0})
        assert again.status_code==200 and again.json()['already_processed'] is True
        rows=client.get('/address-delivery/requests/mine',headers=buyer).json()['items']
        assert len(rows)==2 and {r['state'] for r in rows}=={decision}
        assert {r['shipment_id'] for r in rows}=={shipment_id}
        assert [client.get(f'/products/{pid}').json()['stock'] for pid in products]==([10,10] if decision=='declined' else [8,9])
        for oid,original in originals.items():
            assert client.get(f'/orders/{oid}/purchase-record',headers=buyer).json()['original']==original
            assert client.get(f'/orders/{oid}/purchase-record',headers=outsider).status_code==404

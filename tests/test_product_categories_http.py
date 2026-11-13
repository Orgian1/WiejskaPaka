"""Taxonomy, combined filters, private edits and unchanged checkout data."""
import uuid
import pytest
from fastapi.testclient import TestClient
from backend import app as module,address_delivery
from backend.product_categories import CATEGORIES


def account(client,role):
    data={'email':uuid.uuid4().hex+'@example.invalid','password':'PrivateCatalogPassword2026','role':role}
    result=client.post('/auth/register',json=data);assert result.status_code==201
    return {'Authorization':'Bearer '+client.post('/auth/login',json=data).json()['access_token']}


def exercise_catalog(client):
    farmers=[account(client,'rolnik') for _ in range(3)];buyer=account(client,'klient');tag=uuid.uuid4().hex[:12]
    points=[]
    for i,farmer in enumerate(farmers[:2]):
        response=client.post('/pickup-points',headers=farmer,json={'name':'Punkt '+tag,'city':'Warszawa','street':'Testowa 1','opening_hours':'9-16','latitude_e6':52000000+i*100000,'longitude_e6':21000000})
        assert response.status_code==201,response.text;points.append(response.json()['id'])
    window=client.post('/address-delivery/windows',headers=farmers[0],json={'city':'Warszawa','postal_code':'00-001','weekday':1,'from_time':'09:00','to_time':'16:00'})
    assert window.status_code==200,window.text
    products=[]
    for owner,name,stock,category,sub in [(0,'Pomidory',3,'vegetables','vegetables-tomatoes'),(0,'Jabłka',0,'fruit','fruit-apples'),(1,'Miód lipowy',5,'honey','honey-linden'),(2,'Produkt mieszany',4,'other','other-other')]:
        response=client.post('/products',headers=farmers[owner],json={'name':tag+' '+name,'stock':stock,'price_grosze':299,'delivery_grosze':501,'category_id':category,'subcategory_id':sub,'description':'Opis <bez HTML>'})
        assert response.status_code==201,response.text;products.append(response.json()['id'])
    def query(**kwargs):
        result=client.post('/catalog/query',json={'q':tag,**kwargs});assert result.status_code==200,result.text;return result.json()
    assert query()['total']==4
    assert [p['id'] for p in query(category_id='vegetables',subcategory_id='vegetables-tomatoes',available_now=True,fulfillment='dostawa')['items']]==[products[0]]
    assert query(available_now=True)['total']==2
    assert query(fulfillment='odbior')['total']==3 and query(fulfillment='dostawa')['total']==2
    assert query(q=tag+' Pomidory',category_id='fruit')['total']==0
    nearest=query(sort='nearest',latitude_e6=52000000,longitude_e6=21000000)
    distances={p['id']:p['distance_m'] for p in nearest['items']}
    assert distances[products[0]]==0 and distances[products[2]]>10000 and distances[products[3]] is None
    assert nearest['items'][-1]['id']==products[3]
    assert len({p['id'] for p in query(limit=2)['items']+query(limit=2,offset=2)['items']})==4
    for body in [{'sort':'nearest'},{'category_id':'bad'},{'category_id':'fruit','subcategory_id':'vegetables-tomatoes'},{'latitude_e6':True,'longitude_e6':21}]:
        assert client.post('/catalog/query',json=body).status_code==422
    url='/products/mine/'+str(products[0])
    assert client.patch(url,headers=farmers[1],json={'category_id':'fruit'}).status_code==404
    assert client.patch(url,headers=buyer,json={'description':'cudzy'}).status_code==403
    assert client.patch(url,headers=farmers[0],json={'description':'bad\u0000text'}).status_code==422
    before=client.get('/products/'+str(products[0])).json()
    assert client.patch(url,headers=farmers[0],json={'stock':99,'category_id':'fruit','subcategory_id':'vegetables-tomatoes'}).status_code==422
    assert client.get('/products/'+str(products[0])).json()['stock']==before['stock']
    cart=client.put('/cart/items',headers=buyer,json={'product_id':products[0],'quantity':1});assert cart.status_code==200
    order=client.post('/orders',headers=buyer,json={'product_id':products[0],'quantity':1,'fulfillment':'odbior','pickup_point_id':points[0]});assert order.status_code==201,order.text
    old_order=client.get('/orders/me',headers=buyer).json()
    saved=client.patch(url,headers=farmers[0],json={'category_id':'fruit','subcategory_id':'fruit-apples','description':'Poprawiony opis'})
    assert saved.status_code==200 and saved.json()['description']=='Poprawiony opis'
    assert client.get('/orders/me',headers=buyer).json()==old_order
    assert [(p['product_id'],p['quantity']) for p in client.get('/cart/items',headers=buyer).json()['items']]==[(products[0],1)]
    assert query(category_id='fruit')['total']==2
    assert query(q=tag+' Pomidory')['items'][0]['price_grosze']==299
    return farmers[0],products[0],tag


def test_catalog_contract_sqlite(monkeypatch):
    monkeypatch.setenv('WP_ENABLE_ADDRESS_DELIVERY','1');monkeypatch.setenv('WP_ENABLE_PICKUP_DATES','0')
    with module.db() as con:con.executescript(address_delivery.SCHEMA_SQLITE)
    exercise_catalog(TestClient(module.app))


def test_sixteen_stable_categories_and_valid_children():
    data=TestClient(module.app).get('/product-categories').json()['categories']
    assert len(data)==16 and data==CATEGORIES and len({c['id'] for c in data})==16
    assert [c['label'] for c in data]==['Warzywa','Owoce','Miody','Przetwory','Nabiał','Mięso','Jaja','Pieczywo','Ryby','Zboża i mąki','Zioła i przyprawy','Grzyby','Orzechy i nasiona','Soki i napoje','Sadzonki i rośliny','Pozostałe']
    assert all(s['id'].startswith(c['id']+'-') for c in data for s in c['subcategories'])


@pytest.fixture(scope='module')
def catalog_seller():
    client=TestClient(module.app)
    return client,account(client,'rolnik')


@pytest.mark.parametrize('category',CATEGORIES,ids=lambda c:c['id'])
def test_each_category_can_be_saved_and_searched(catalog_seller,category):
    client,farmer=catalog_seller;name=uuid.uuid4().hex
    result=client.post('/products',headers=farmer,json={'name':name,'stock':2,'price_grosze':199,'delivery_grosze':0,'category_id':category['id'],'subcategory_id':category['subcategories'][0]['id']})
    assert result.status_code==201
    found=client.post('/catalog/query',json={'q':name,'category_id':category['id'],'subcategory_id':category['subcategories'][0]['id']})
    assert found.status_code==200 and [p['id'] for p in found.json()['items']]==[result.json()['id']]

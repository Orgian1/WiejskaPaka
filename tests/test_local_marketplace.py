"""API integration and independent great-circle checks for local offer discovery."""
import math
import random
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient
from backend import app as api
from backend.local_marketplace import EARTH_RADIUS_M, nearby_offers, refresh_product_index, search_key, sphere
from tests.test_b10921_security_boundaries import actor


def setup_market(*, lat=52_000_000,lon=16_000_000,stock=10,name='Ziemniaki ŁĄKOWE'):
    client=TestClient(api.app)
    farmer,fid=actor('rolnik');buyer,bid=actor('klient')
    product=client.post('/products',headers=farmer,json={'name':name,'price_grosze':199,'delivery_grosze':501,'stock':stock})
    assert product.status_code==201,product.text
    body={'name':'Przystanek '+uuid4().hex[:6],'city':'Opole','street':'Polna 1','opening_hours':'9:00–17:00',
          'latitude_e6':lat,'longitude_e6':lon}
    point=client.post('/pickup-points',headers=farmer,json=body)
    assert point.status_code==201,point.text
    return client,farmer,buyer,fid,product.json()['id'],point.json()['id'],body


def query(client,lat=52_000_000,lon=16_000_000,**kwargs):
    return client.post('/marketplace/nearby',json={'latitude_e6':lat,'longitude_e6':lon,'radius_m':1000,**kwargs})


def test_search_shows_one_public_point_product_and_integer_prices():
    c,f,b,fid,pid,point,body=setup_market()
    r=query(c,q='ZIEMNIAKI LAKOWE')
    assert r.status_code==200,r.text
    offer=next(i for i in r.json()['items'] if i['product']['id']==pid)
    assert offer['distance_m']==0 and offer['distance_bucket_m']==100
    assert offer['pickup_point']['id']==point and offer['product']['price_grosze']==199
    assert set(offer)=={'distance_m','distance_bucket_m','product','pickup_point'}
    assert set(offer['pickup_point'])=={'id','name','city','street','opening_hours'}
    assert all(x not in r.text for x in ('password_hash','pin_hash','token_hash','@example','delivery_street','latitude_e6','longitude_e6','phone'))
    assert r.headers['cache-control']=='no-store' and r.headers['pragma']=='no-cache'
    assert 'geolocation=(self)' in r.headers['permissions-policy']


@pytest.mark.parametrize('radius',[100,500,1000,5000])
def test_required_radii_match_independent_distance_oracle(radius):
    c,f,b,fid,pid,point,body=setup_market(lat=10_000_000,lon=20_000_000)
    rng=random.Random(radius)
    fixtures={point:(10_000_000,20_000_000)}
    for _ in range(16):
        lat=10_000_000+rng.randint(-60_000,60_000)
        lon=20_000_000+rng.randint(-60_000,60_000)
        p=c.post('/pickup-points',headers=f,json={**body,'latitude_e6':lat,'longitude_e6':lon})
        assert p.status_code==201
        fixtures[p.json()['id']]=(lat,lon)
    result=query(c,10_000_000,20_000_000,radius_m=radius,limit=100).json()
    def distance(lat,lon):
        a,b=math.radians(10),math.radians(lat/1e6)
        dlat,dlon=b-a,math.radians((lon-20_000_000)/1e6)
        h=math.sin(dlat/2)**2+math.cos(a)*math.cos(b)*math.sin(dlon/2)**2
        return 2*EARTH_RADIUS_M*math.atan2(math.sqrt(h),math.sqrt(1-h))
    expected=sorted([(distance(*v),k) for k,v in fixtures.items() if distance(*v)<=radius])
    actual=[i for i in result['items'] if i['product']['id']==pid]
    assert [i['pickup_point']['id'] for i in actual]==[k for d,k in expected]
    for item,(d,k) in zip(actual,expected):
        assert abs(item['distance_m']-math.ceil(d))<=1
        assert item['distance_bucket_m'] in (100,500,1000,5000)


@pytest.mark.parametrize('lat,lon,search_lat,search_lon',[
    (0,179_999_900,0,-179_999_900),
    (90_000_000,45_000_000,90_000_000,-135_000_000),
    (-90_000_000,180_000_000,-90_000_000,-180_000_000),
    (0,180_000_000,0,-180_000_000),
])
def test_antimeridian_and_poles(lat,lon,search_lat,search_lon):
    c,f,b,fid,pid,point,body=setup_market(lat=lat,lon=lon)
    offers=query(c,search_lat,search_lon,radius_m=100).json()['items']
    offer=next(i for i in offers if i['product']['id']==pid)
    assert offer['distance_m']<=23


@pytest.mark.parametrize('field,value',[
    ('latitude_e6',90_000_001),('latitude_e6',-90_000_001),('longitude_e6',180_000_001),
    ('latitude_e6',True),('longitude_e6','16000000'),('latitude_e6',52_000_000.0),
    ('radius_m',100.0),('radius_m',True),('radius_m',200),('radius_m',10000),
    ('min_price_grosze',1.5),('max_price_grosze','100'),('max_price_grosze',True),
    ('limit',0),('limit',101),('offset',10001),('q','x'*121),
])
def test_strict_bounded_inputs_do_not_echo_location(field,value):
    c=TestClient(api.app)
    r=query(c,**{field:value})
    assert r.status_code==422,r.text
    assert 'input' not in r.text and 'ctx' not in r.text


def test_bad_price_range_is_rejected():
    assert query(TestClient(api.app),min_price_grosze=200,max_price_grosze=100).status_code==422


@pytest.mark.parametrize('term',['%','_',"' OR 1=1 --"])
def test_literal_queries_do_not_act_as_patterns_or_sql(term):
    c,f,b,fid,pid,point,body=setup_market(name='Jabłka '+term)
    result=query(c,q=term).json()['items']
    assert any(i['product']['id']==pid for i in result)
    assert all(search_key(term) in search_key(i['product']['name']) for i in result)


def test_stock_price_and_product_renaming_are_live():
    c,f,b,fid,pid,point,body=setup_market()
    assert not any(i['product']['id']==pid for i in query(c,max_price_grosze=198).json()['items'])
    changed=c.patch(f'/products/mine/{pid}',headers=f,json={'name':'ŚWIEŻA ŚLIWKA','price_grosze':299})
    assert changed.status_code==200,changed.text
    assert any(i['product']['id']==pid for i in query(c,q='swieza sliwka',min_price_grosze=299,max_price_grosze=299).json()['items'])
    assert not any(i['product']['id']==pid for i in query(c,q='ziemniaki').json()['items'])
    assert c.patch(f'/products/mine/{pid}',headers=f,json={'stock':0}).status_code==200
    assert not any(i['product']['id']==pid for i in query(c).json()['items'])


def test_farmer_can_disable_point_without_cancelling_existing_pickup():
    c,f,b,fid,pid,point,body=setup_market()
    order=c.post('/orders',headers=b,json={'product_id':pid,'quantity':1,'fulfillment':'odbior','pickup_point_id':point})
    assert order.status_code==201
    assert c.put(f'/pickup-points/{point}',headers=f,json={**body,'active':False}).status_code==200
    assert not any(i['pickup_point']['id']==point for i in query(c).json()['items'])
    assert all(p['id']!=point for p in c.get(f'/farmers/{fid}/pickup-points').json())
    assert c.post('/orders',headers=b,json={'product_id':pid,'quantity':1,'fulfillment':'odbior','pickup_point_id':point}).status_code==422
    oid=order.json()['id']
    assert c.post(f'/test/orders/{oid}/ready',headers=f).status_code==200
    assert c.post(f'/orders/{oid}/confirm',headers=f,json={'pin':order.json()['pin_test_only'],'checked_goods':True}).json()['confirmed']


@pytest.mark.parametrize('change',[
    {'street':'Inna 99'},{'opening_hours':'00:00–01:00'},
    {'latitude_e6':52_000_100},{'clear_coordinates':True},
])
def test_open_order_prevents_silent_change_of_pickup_contract(change):
    c,f,b,fid,pid,point,body=setup_market()
    oid=c.post('/orders',headers=b,json={'product_id':pid,'quantity':1,'fulfillment':'odbior','pickup_point_id':point}).json()['id']
    update={**body,'active':True,**change}
    if change.get('clear_coordinates'):
        update.pop('latitude_e6');update.pop('longitude_e6')
    r=c.put(f'/pickup-points/{point}',headers=f,json=update)
    assert r.status_code==409,r.text
    saved=next(p for p in c.get('/farmers/me/pickup-points',headers=f).json() if p['id']==point)
    assert saved['street']=='Polna 1' and saved['latitude_e6']==52_000_000
    assert c.post(f'/orders/{oid}/cancel-test',headers=b).status_code==200
    assert c.put(f'/pickup-points/{point}',headers=f,json=update).status_code==200


def test_only_owner_farmer_can_edit_point():
    c,f,b,fid,pid,point,body=setup_market()
    other,_=actor('rolnik');courier,_=actor('dostawca')
    url=f'/pickup-points/{point}';update={**body,'active':False}
    assert c.put(url,json=update).status_code==401
    assert c.put(url,headers=b,json=update).status_code==403
    assert c.put(url,headers=courier,json=update).status_code==403
    assert c.put(url,headers=other,json=update).status_code==404
    assert any(i['pickup_point']['id']==point for i in query(c).json()['items'])


@pytest.mark.parametrize('extra',[
    {'latitude_e6':True},{'longitude_e6':16.0},{'latitude_e6':None},
    {'latitude_e6':52_000_000,'longitude_e6':None},{'active':1},
    {'clear_coordinates':True},
])
def test_point_updates_validate_atomically(extra):
    c,f,b,fid,pid,point,body=setup_market()
    r=c.put(f'/pickup-points/{point}',headers=f,json={**body,'active':True,**extra})
    assert r.status_code==422,r.text
    assert c.get('/farmers/me/pickup-points',headers=f).json()[0]['active']==1


def test_unknown_coordinates_are_not_guessed_and_clear_is_explicit():
    c,f,b,fid,pid,point,body=setup_market()
    update={k:v for k,v in body.items() if k not in ('latitude_e6','longitude_e6')}
    assert c.put(f'/pickup-points/{point}',headers=f,json={**update,'active':True}).status_code==200
    assert any(i['pickup_point']['id']==point for i in query(c).json()['items'])
    assert c.put(f'/pickup-points/{point}',headers=f,json={**update,'active':True,'clear_coordinates':True}).status_code==200
    assert not any(i['pickup_point']['id']==point for i in query(c).json()['items'])
    assert any(p['id']==point for p in c.get(f'/farmers/{fid}/pickup-points').json())


def test_stable_pagination_without_duplicate_offers():
    c,f,b,fid,pid,point,body=setup_market(lat=-10_000_000,lon=-20_000_000)
    for _ in range(4):
        assert c.post('/pickup-points',headers=f,json=body).status_code==201
    results=[]
    for offset in (0,2,4):
        r=query(c,-10_000_000,-20_000_000,q='ziemniaki',limit=2,offset=offset).json()
        assert r['has_more']==(offset<4)
        results.extend((i['pickup_point']['id'],i['product']['id']) for i in r['items'])
    assert len(results)==len(set(results))==5
    assert results==sorted(results)


def test_index_backfills_legacy_names_and_catalog_handles_polish():
    c,f,b,fid,pid,point,body=setup_market(name='ŁÓDZKIE ŻÓŁTE ŚLIWKI')
    with api.db() as con:
        con.execute('DELETE FROM product_search_names WHERE product_id=?',(pid,))
        assert refresh_product_index(con)>=1
    r=c.get('/catalog/search',params={'q':'lodzkie zolte sliwki'}).json()
    assert any(i['id']==pid for i in r['items'])


def test_customer_location_is_not_persisted():
    c,*_=setup_market()
    with api.db() as con:
        before=list(con.iterdump())
    assert query(c,51_234_567,15_765_432,q='żółte').status_code==200
    with api.db() as con:
        assert list(con.iterdump())==before


def test_failed_point_coordinate_write_rolls_back_metadata(monkeypatch):
    from backend import local_marketplace
    c,f,b,fid,pid,point,body=setup_market()
    def fail(*args):raise RuntimeError('coordinate failure')
    monkeypatch.setattr(local_marketplace,'save_coordinates',fail)
    r=TestClient(api.app,raise_server_exceptions=False).put(f'/pickup-points/{point}',headers=f,
        json={**body,'street':'Inna 99','latitude_e6':51_000_000,'active':False})
    assert r.status_code==500 and 'coordinate failure' not in r.text
    saved=next(p for p in c.get('/farmers/me/pickup-points',headers=f).json() if p['id']==point)
    assert saved['active']==1 and saved['street']=='Polna 1' and saved['latitude_e6']==52_000_000


def test_failed_product_index_write_rolls_back_product_update(monkeypatch):
    from backend import local_marketplace
    c,f,b,fid,pid,point,body=setup_market()
    def fail(*args):raise RuntimeError('index failure')
    monkeypatch.setattr(local_marketplace,'index_product',fail)
    r=TestClient(api.app,raise_server_exceptions=False).patch(f'/products/mine/{pid}',headers=f,json={'name':'Inny produkt'})
    assert r.status_code==500
    assert c.get(f'/products/{pid}').json()['name']=='Ziemniaki ŁĄKOWE'


@pytest.mark.parametrize('radius',[100,500,1000,5000])
def test_distance_boundary_includes_inside_and_excludes_outside(radius):
    c,f,b,fid,pid,point,body=setup_market(lat=0,lon=0)
    angular=radius/EARTH_RADIUS_M*180/math.pi*1_000_000
    inner=int(math.floor(angular));outer=int(math.ceil(angular))
    inside=c.post('/pickup-points',headers=f,json={**body,'latitude_e6':inner,'longitude_e6':0}).json()['id']
    outside=c.post('/pickup-points',headers=f,json={**body,'latitude_e6':outer,'longitude_e6':0}).json()['id']
    found={i['pickup_point']['id'] for i in query(c,0,0,radius_m=radius,limit=100).json()['items'] if i['product']['id']==pid}
    assert inside in found and outside not in found


def test_point_edit_and_checkout_are_serialized():
    from concurrent.futures import ThreadPoolExecutor
    c,f,b,fid,pid,point,body=setup_market()
    with ThreadPoolExecutor(max_workers=2) as pool:
        order=pool.submit(c.post,'/orders',headers=b,json={'product_id':pid,'quantity':1,'fulfillment':'odbior','pickup_point_id':point})
        update=pool.submit(c.put,f'/pickup-points/{point}',headers=f,json={**body,'street':'Nowa 99','active':True})
        r_order,r_update=order.result(),update.result()
    assert r_order.status_code==201
    assert r_update.status_code in (200,409)
    # Once an order exists, subsequent changes must always be blocked.
    assert c.put(f'/pickup-points/{point}',headers=f,json={**body,'street':'Trzecia 99','active':True}).status_code==409


def test_disabled_point_cannot_be_bought_from_saved_cart():
    c,f,b,fid,pid,point,body=setup_market()
    assert c.put('/cart/items',headers=b,json={'product_id':pid,'quantity':1}).status_code==200
    assert c.put(f'/pickup-points/{point}',headers=f,json={**body,'active':False}).status_code==200
    response=c.post('/cart/checkout-test',headers=b,json={'fulfillment':'odbior','pickup_point_id':point})
    assert response.status_code==422
    with api.db() as con:
        assert con.execute('SELECT stock FROM products WHERE id=?',(pid,)).fetchone()['stock']==10
        assert con.execute('SELECT COUNT(*) AS n FROM orders WHERE product_id=?',(pid,)).fetchone()['n']==0

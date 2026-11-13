"""Photon contract, public-demo budgets, proxy routing and explicit launcher opt-in."""
import asyncio
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
import json
from unittest.mock import patch
import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from backend import address_search,photon_geocoder as photon
from scripts.run_phone_demo import full_demo_environment,enable_public_geocoder,main


def feature(**changes):
    item={'type':'Feature','geometry':{'type':'Point','coordinates':[Decimal('21.0122295'),Decimal('52.2296765')]},
          'properties':{'countrycode':'PL','name':'Warszawa','city':'Warszawa','country':'Polska'}}
    item.update(changes);return item


def response(*features):return {'type':'FeatureCollection','features':list(features)}
def client():
    app=FastAPI();app.include_router(address_search.router);return TestClient(app)


def test_photon_decimal_coordinates_labels_and_foreign_filter():
    items=photon.normalize(response(feature(),feature(properties={'countrycode':'DE','name':'Berlin'})))
    assert len(items)==1 and items[0]['label']=='Warszawa, Polska'
    assert (items[0]['latitude_e6'],items[0]['longitude_e6'])==(52229677,21012230)
    assert 'Photon' in items[0]['notice']


@pytest.mark.parametrize('coordinates',[[True,52],[21,'52'],[21,91],[181,52],[float('nan'),52],[21,52,1],None])
def test_invalid_photon_coordinates_are_rejected(coordinates):
    with pytest.raises(ValueError):photon.normalize(response(feature(geometry={'type':'Point','coordinates':coordinates})))


def test_bad_geometry_labels_and_excess_results_fail_closed():
    for data in [response(feature(geometry={'type':'LineString','coordinates':[[21,52]]})),
                 response(feature(properties={'countrycode':'PL','name':'Private\nvalue'})),response(*[feature() for _ in range(6)]),{},response(None)]:
        with pytest.raises(ValueError):photon.normalize(data)


def test_real_photon_transport_sends_bounded_polish_query_without_bearer():
    def handle(request):
        assert request.url.scheme=='https' and request.url.host=='photon.komoot.io'
        assert request.url.params==httpx.QueryParams({'q':'Testowa 7, 00-001, Warszawa','countrycode':'PL','lang':'default','limit':'5'})
        assert 'authorization' not in request.headers and 'cookie' not in request.headers
        return httpx.Response(200,content=b'{"type":"FeatureCollection","features":[{"type":"Feature","geometry":{"type":"Point","coordinates":[21.0122295,52.2296765]},"properties":{"countrycode":"PL","name":"Warszawa"}}]}')
    result=asyncio.run(photon.lookup(address_search.AddressQuery(city='Warszawa',street='Testowa 7',postal_code='00-001'),photon.PUBLIC_URL,transport=httpx.MockTransport(handle)))
    assert result[0]['latitude_e6']==52229677 and result[0]['longitude_e6']==21012230


@pytest.mark.parametrize('upstream',[httpx.Response(302,headers={'Location':'https://other.invalid'}),httpx.Response(200,content=b' '*65537)])
def test_no_redirects_or_unbounded_response(upstream):
    with pytest.raises((ValueError,httpx.HTTPError)):
        asyncio.run(photon.lookup(address_search.AddressQuery(city='Warszawa'),photon.PUBLIC_URL,transport=httpx.MockTransport(lambda _:upstream)))


def test_public_budget_rate_hourly_limit_and_concurrency():
    budget=photon.PublicBudget()
    with ThreadPoolExecutor(max_workers=20) as pool:delays=list(pool.map(lambda _:budget.reserve(now=10),range(20)))
    assert delays.count(0)==1 and delays.count(1)==19
    budget=photon.PublicBudget()
    for n in range(120):assert budget.reserve(now=2*n)==0
    assert budget.reserve(now=240)==3360
    assert budget.reserve(now=3600)==0
    assert all(isinstance(t,(int,float)) for t in budget.timestamps)


def test_photon_is_disabled_by_default_and_public_mode_has_rate_limit(monkeypatch):
    monkeypatch.setenv('WP_ADDRESS_SEARCH_PROVIDER','photon');monkeypatch.delenv('WP_ENABLE_ADDRESS_SEARCH',raising=False);monkeypatch.delenv('WP_ADDRESS_SEARCH_URL',raising=False)
    assert client().get('/address-search/config').json()=={'enabled':False}
    monkeypatch.setenv('WP_ENABLE_ADDRESS_SEARCH','1');budget=photon.PublicBudget();monkeypatch.setattr(budget,'reserve',lambda:photon.PublicBudget.reserve(budget,now=10));monkeypatch.setattr(photon,'public_budget',budget)
    calls=[]
    async def lookup(query,url):calls.append((query.city,url));return photon.normalize(response(feature()))
    monkeypatch.setattr(photon,'lookup',lookup)
    c=client();assert c.get('/address-search/config').json()['enabled']
    first=c.post('/address-search',json={'city':'Warszawa'},headers={'Authorization':'Bearer must-not-be-forwarded'})
    assert first.status_code==200 and calls==[('Warszawa',photon.PUBLIC_URL)]
    second=c.post('/address-search',json={'city':'Warszawa'})
    assert second.status_code==429 and int(second.headers['retry-after'])>=1 and len(calls)==1


def test_private_photon_error_does_not_echo_query_or_server(monkeypatch):
    monkeypatch.setenv('WP_ENABLE_ADDRESS_SEARCH','1');monkeypatch.setenv('WP_ADDRESS_SEARCH_PROVIDER','photon');monkeypatch.setenv('WP_ADDRESS_SEARCH_URL','https://own.example/api/')
    async def unavailable(*args):raise ValueError('Warszawa private upstream diagnostic')
    monkeypatch.setattr(photon,'lookup',unavailable)
    result=client().post('/address-search',json={'city':'Warszawa'})
    assert result.status_code==503 and 'Warszawa' not in result.text and 'own.example' not in result.text


def test_unknown_provider_is_disabled(monkeypatch):
    monkeypatch.setenv('WP_ENABLE_ADDRESS_SEARCH','1');monkeypatch.setenv('WP_ADDRESS_SEARCH_PROVIDER','untrusted')
    assert client().get('/address-search/config').json()=={'enabled':False}


def test_explicit_demo_opt_in_preserves_proxy_routes_but_not_unrelated_secrets(tmp_path):
    source={'PATH':'/synthetic/bin','HTTPS_PROXY':'http://proxy.example:8080','SSL_CERT_FILE':'/synthetic/ca.pem',
            'DATABASE_URL':'postgresql://private.invalid/live','PAYU_CLIENT_SECRET':'private',
            'WP_SMTP_PASSWORD':'private','WP_ADDRESS_SEARCH_URL':'https://untrusted.invalid/'}
    original=dict(source);env=full_demo_environment(source,tmp_path/'new.sqlite3')
    assert 'WP_ENABLE_ADDRESS_SEARCH' not in env and 'HTTPS_PROXY' not in env
    enable_public_geocoder(env,source)
    assert env['WP_ENABLE_ADDRESS_SEARCH']=='1' and env['WP_ADDRESS_SEARCH_PROVIDER']=='photon'
    assert env['WP_ADDRESS_SEARCH_URL']==photon.PUBLIC_URL
    assert env['HTTPS_PROXY']==source['HTTPS_PROXY'] and env['SSL_CERT_FILE']==source['SSL_CERT_FILE']
    assert not {'DATABASE_URL','PAYU_CLIENT_SECRET','WP_SMTP_PASSWORD'}.intersection(env)
    assert source==original


def test_launcher_requires_explicit_public_flag_and_keeps_loopback(monkeypatch):
    monkeypatch.setenv('WP_ADDRESS_SEARCH_URL','https://untrusted.invalid/')
    seen=[]
    def launch(command,**kwargs):
        seen.append(kwargs['env']);assert command[command.index('--host')+1]=='127.0.0.1';return 0
    with patch('scripts.run_phone_demo.subprocess.call',side_effect=launch):
        assert main([])==0
        assert main(['--public-geocoder','photon'])==0
    assert 'WP_ENABLE_ADDRESS_SEARCH' not in seen[0]
    assert seen[1]['WP_ADDRESS_SEARCH_URL']==photon.PUBLIC_URL and 'DATABASE_URL' not in seen[1]

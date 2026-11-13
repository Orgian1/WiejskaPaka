"""Reproduce the rejected forced language; exercise the actual endpoint/adapter."""
import asyncio
import ssl
import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from backend import address_search,photon_geocoder


def result():
    return {'type':'FeatureCollection','features':[{'type':'Feature','geometry':{'type':'Point','coordinates':[17.03,51.11]},'properties':{'countrycode':'PL','name':'Wrocław','city':None,'postcode':None,'street':None,'housenumber':None,'state':'Dolnośląskie','country':'Polska'}}]}


def test_forced_unsupported_language_is_a_provider_error():
    # Photon RequestFactoryBase.parseLanguage checks indexed languages. The
    # public search can work while an otherwise identical lang=pl request fails.
    def upstream(request):
        if request.url.params.get('lang')=='pl':return httpx.Response(400,json={'message':'Language is not supported. Supported are: default, en, de, fr'})
        return httpx.Response(200,json=result())
    async def run():
        transport=httpx.MockTransport(upstream)
        async with httpx.AsyncClient(transport=transport) as client:
            bad=await client.get('https://photon.example/api/',params={'q':'Wroclaw','limit':5,'lang':'pl'})
        assert bad.status_code==400
        found=await photon_geocoder.lookup(address_search.AddressQuery(city='Wroclaw'),'https://photon.example/api/',transport=transport)
        assert len(found)==1 and 'Wrocław' in found[0]['label']
    asyncio.run(run())


@pytest.mark.parametrize('payload',[{'city':'Wroclaw'},{'city':'Wrocław'},{'city':'Łódź'},{'city':'Wrocław','street':'Świdnicka 1','postal_code':'50-001'},{'postal_code':'50-001'},{'street':'Świdnicka 1'}])
def test_endpoint_uses_local_names_polish_filter_and_handles_optional_nulls(monkeypatch,payload):
    monkeypatch.setenv('WP_ENABLE_ADDRESS_SEARCH','1');monkeypatch.setenv('WP_ADDRESS_SEARCH_PROVIDER','photon');monkeypatch.setenv('WP_ADDRESS_SEARCH_URL','https://photon.example/api/')
    seen=[]
    def upstream(request):
        seen.append(request)
        assert request.url.params['lang']=='default' and request.url.params['countrycode']=='PL'
        assert 'authorization' not in request.headers and 'cookie' not in request.headers
        return httpx.Response(200,json=result())
    real=photon_geocoder.lookup
    async def lookup(query,url):return await real(query,url,transport=httpx.MockTransport(upstream))
    monkeypatch.setattr(photon_geocoder,'lookup',lookup)
    app=FastAPI();app.include_router(address_search.router)
    response=TestClient(app).post('/address-search',json=payload,headers={'Authorization':'Bearer private-synthetic'})
    assert response.status_code==200 and response.json()['items'][0]['latitude_e6']==51110000
    assert seen[0].url.params['q']==', '.join(filter(None,(payload.get('street'),payload.get('postal_code'),payload.get('city'))))


def test_default_context_keeps_certificate_and_hostname_verification():
    context=ssl.create_default_context()
    assert context.check_hostname and context.verify_mode==ssl.CERT_REQUIRED


def test_bad_trust_configuration_is_sanitized_service_unavailable(monkeypatch):
    monkeypatch.setenv('WP_ENABLE_ADDRESS_SEARCH','1');monkeypatch.setenv('WP_ADDRESS_SEARCH_PROVIDER','photon');monkeypatch.setenv('WP_ADDRESS_SEARCH_URL','https://photon.example/api/')
    def broken():raise OSError('private-ca-path')
    app=FastAPI();app.include_router(address_search.router);client=TestClient(app)
    monkeypatch.setattr(photon_geocoder.ssl,'create_default_context',broken)
    response=client.post('/address-search',json={'city':'Wroclaw'})
    assert response.status_code==503 and 'private-ca-path' not in response.text

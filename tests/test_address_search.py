import asyncio

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend import address_search as module


def client():
    app = FastAPI()
    app.include_router(module.router)
    return TestClient(app)


def test_disabled_search_never_connects(monkeypatch):
    monkeypatch.delenv('WP_ENABLE_ADDRESS_SEARCH', raising=False)
    c = client()
    assert c.get('/address-search/config').json() == {'enabled': False}
    response = c.post('/address-search', json={'city': 'Legnica'})
    assert response.status_code == 503


@pytest.mark.parametrize('url', [
    '', 'http://geo.example/search', 'https://user:secret@geo.example/search',
    'https://geo.example/search?secret=hidden', 'https://geo.example/search#part',
    'https://nominatim.openstreetmap.org/search',
    'https://NOMINATIM.OPENSTREETMAP.ORG./search',
])
def test_invalid_or_public_provider_is_not_enabled(monkeypatch, url):
    monkeypatch.setenv('WP_ENABLE_ADDRESS_SEARCH', '1')
    monkeypatch.setenv('WP_ADDRESS_SEARCH_URL', url)
    assert client().get('/address-search/config').json()['enabled'] is False


@pytest.mark.parametrize('body', [
    {'city': ' '}, {'city': 'Legnica\n'}, {'city': 'Legnica', 'postal_code': '12345'},
    {'city': 'Legnica', 'url': 'https://unexpected.example'},
])
def test_bad_queries_are_rejected(body):
    assert client().post('/address-search', json=body).status_code == 422


def test_real_adapter_uses_structured_query_and_preserves_multiple_candidates():
    def handle(request):
        assert request.url.host == 'geo.example'
        assert request.url.params['city'] == 'Wojciechów'
        assert request.url.params['postalcode'] == '59-516'
        assert request.url.params['countrycodes'] == 'pl'
        assert 'q' not in request.url.params
        assert 'authorization' not in request.headers
        return httpx.Response(200, json=[
            {'display_name': 'Wojciechów, gmina Zagrodno', 'lat': '51.1234565', 'lon': '15.25'},
            {'display_name': 'Inny wynik', 'lat': '50', 'lon': '16'},
        ])
    result = asyncio.run(module.lookup(
        module.AddressQuery(city='Wojciechów', postal_code='59-516'),
        'https://geo.example/search', transport=httpx.MockTransport(handle)))
    assert len(result) == 2
    assert result[0]['latitude_e6'] == 51123457
    assert result[0]['longitude_e6'] == 15250000


@pytest.mark.parametrize('lat', ['NaN', 'Infinity', '91', None, 51.2])
def test_invalid_provider_coordinates_fail_closed(lat):
    with pytest.raises(ValueError):
        module.normalize_results([{'display_name': 'Testowo', 'lat': lat, 'lon': '16'}])


def test_no_redirects_or_oversized_responses():
    for response in [httpx.Response(302, headers={'Location': 'https://other.example'}),
                     httpx.Response(200, content=b' ' * 65537)]:
        with pytest.raises((ValueError, httpx.HTTPError)):
            asyncio.run(module.lookup(module.AddressQuery(city='Legnica'),
                'https://geo.example/search', transport=httpx.MockTransport(lambda _: response)))


def test_provider_error_does_not_echo_address(monkeypatch):
    monkeypatch.setenv('WP_ENABLE_ADDRESS_SEARCH', '1')
    monkeypatch.setenv('WP_ADDRESS_SEARCH_URL', 'https://geo.example/search')
    async def unavailable(*args):
        raise ValueError('Private address in upstream failure')
    monkeypatch.setattr(module, 'lookup', unavailable)
    response = client().post('/address-search', json={'city': 'Legnica'})
    assert response.status_code == 503
    assert 'Private' not in response.text and 'geo.example' not in response.text

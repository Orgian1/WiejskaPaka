import httpx
from fastapi.testclient import TestClient

from backend import public_demo


def test_public_demo_displays_catalog_but_has_no_account_api(monkeypatch):
    calls = []

    def preview(path, params=None):
        calls.append(path)
        assert path == '/catalog/search'
        assert params == {'limit': 24, 'offset': 0}
        items = [{'id': 1, 'name': '<script>test</script>', 'price_grosze': 1205, 'sale_unit': 'kg'}]
        return httpx.Response(
            200, json={'items': items, 'total': 25}, request=httpx.Request('GET', 'http://localhost')
        )

    monkeypatch.setattr(public_demo, 'get_preview', preview)
    with TestClient(public_demo.app) as client:
        response = client.get('/')
        assert response.status_code == 200
        assert '&lt;script&gt;test&lt;/script&gt;' in response.text
        assert '12,05 zł / kg' in response.text
        assert 'href="/?page=2"' in response.text
        assert '/assets/' + public_demo.AD in response.text
        assert client.get('/assets/' + public_demo.AD).status_code == 200
        for path in ('/auth/login', '/auth/register', '/cart/items', '/wallet', '/catalog/search'):
            assert client.post(path, json={}).status_code == 404
        assert client.get('/assets/index.html').status_code == 404
    assert calls == ['/catalog/search']


def test_photo_requires_public_product(monkeypatch):
    calls = []

    def preview(path, params=None):
        calls.append(path)
        return httpx.Response(404)

    monkeypatch.setattr(public_demo, 'get_preview', preview)
    with TestClient(public_demo.app) as client:
        assert client.get('/foto/123').status_code == 404
    assert calls == ['/products/123']

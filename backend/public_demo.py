"""Read-only storefront on its own listener, with no access to the test API."""
from html import escape
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, HTMLResponse, Response
import httpx

WEB = Path(__file__).resolve().parents[1] / 'web'
AD = 'wiejskapaka-reklama-logowanie-20261122.webp'
PAGE_SIZE = 24
UPSTREAM = 'http://127.0.0.1:8001'
ASSETS = {'style.css', 'public-demo.css', AD}

app = FastAPI(openapi_url=None, docs_url=None, redoc_url=None)


@app.middleware('http')
async def demo_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers['Content-Security-Policy'] = (
        "default-src 'none'; style-src 'self'; img-src 'self'; "
        "base-uri 'none'; frame-ancestors 'none'; form-action 'none'"
    )
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'no-referrer'
    return response


def get_preview(path, params=None):
    with httpx.Client(timeout=3, trust_env=False) as client:
        return client.get(UPSTREAM + path, params=params)


@app.get('/assets/{name}')
def asset(name: str):
    if name not in ASSETS:
        raise HTTPException(404)
    return FileResponse(WEB / name)


@app.get('/foto/{product_id}')
def photo(product_id: int):
    if not 0 < product_id < 2**63:
        raise HTTPException(404)
    try:
        if get_preview(f'/products/{product_id}').status_code != 200:
            raise HTTPException(404)
        image = get_preview(f'/user-photos/product/{product_id}')
    except httpx.HTTPError:
        raise HTTPException(503) from None
    if image.status_code != 200 or image.headers.get('content-type') != 'image/jpeg':
        raise HTTPException(404)
    return Response(image.content, media_type='image/jpeg')


def product_card(item):
    unit = {'szt': 'szt.', 'kg': 'kg', 'g': 'g', 'l': 'l', 'ml': 'ml', 'opak': 'opak.',
            'peczek': 'pęczek', 'sloik': 'słoik', 'butelka': 'butelka',
            'worek': 'worek', 'skrzynka': 'skrzynka', 'tacka': 'tacka'}.get(
        item.get('sale_unit'), 'szt.'
    )
    price, pennies = divmod(item['price_grosze'], 100)
    return (
        f'<article><img class="demo-product-photo" src="/foto/{item["id"]}" alt="" loading="lazy">'
        f'<h3>{escape(item["name"])}</h3><p>{price},{pennies:02d} zł / {unit}</p></article>'
    )


@app.get('/', response_class=HTMLResponse)
def index(page: int = Query(default=1, ge=1, le=417)):
    offset = (page - 1) * PAGE_SIZE
    try:
        upstream = get_preview('/catalog/search', {'limit': PAGE_SIZE, 'offset': offset})
        upstream.raise_for_status()
        catalog = upstream.json()
        cards = ''.join(product_card(item) for item in catalog['items'])
        links = []
        if page > 1:
            links.append(f'<a href="/?page={page - 1}">Poprzednia strona</a>')
        if offset + PAGE_SIZE < catalog['total'] and page < 417:
            links.append(f'<a href="/?page={page + 1}">Następna strona</a>')
        pagination = '<nav class="demo-pagination" aria-label="Strony katalogu">' + ' '.join(links) + '</nav>' if links else ''
        products = f'<div class="demo-products">{cards}</div>' if cards else '<p>W katalogu nie ma jeszcze produktów.</p>'
        status = 200
    except (httpx.HTTPError, ValueError, KeyError, TypeError):
        products = '<p>Katalog jest chwilowo niedostępny. Spróbuj ponownie później.</p>'
        pagination = ''
        status = 503
    html = (WEB / 'public-demo.html').read_text(encoding='utf-8')
    return HTMLResponse(
        html.replace('<!-- demo-catalog -->', products + pagination).replace('<!-- demo-banner -->', AD),
        status_code=status,
    )

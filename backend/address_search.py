"""Explicit address search against an operator-configured Nominatim service.

No default public provider, persistence, redirects or account credentials.
The configured provider receives the address only after the user clicks search.
"""
import json
import os
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from urllib.parse import urlsplit

import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator

router = APIRouter()


class AddressQuery(BaseModel):
    model_config = ConfigDict(extra='forbid')
    city: str = Field(min_length=2, max_length=120)
    street: str = Field(default='', max_length=180)
    postal_code: str = Field(default='', pattern=r'^(?:[0-9]{2}-[0-9]{3})?$')

    @field_validator('city', 'street', mode='before')
    @classmethod
    def clean_text(cls, value):
        if not isinstance(value, str) or any(ord(c) < 32 for c in value):
            raise ValueError('Podaj poprawny adres')
        return value.strip()


def provider_url():
    if os.environ.get('WP_ENABLE_ADDRESS_SEARCH') != '1':
        return None
    url = os.environ.get('WP_ADDRESS_SEARCH_URL', '').strip()
    parsed = urlsplit(url)
    host = (parsed.hostname or '').lower().rstrip('.')
    if (parsed.scheme != 'https' or not host or parsed.username or parsed.password
            or parsed.query or parsed.fragment
            or host == 'openstreetmap.org' or host.endswith('.openstreetmap.org')):
        raise ValueError('Skonfiguruj własną lub zakontraktowaną usługę geokodowania HTTPS')
    return url


def microdegrees(value, limit):
    if not isinstance(value, str) or len(value) > 32:
        raise ValueError('Nieprawidłowa odpowiedź lokalizacji')
    try:
        number = Decimal(value)
        if not number.is_finite() or abs(number) > limit:
            raise ValueError('Nieprawidłowa odpowiedź lokalizacji')
        return int((number * 1_000_000).quantize(Decimal('1'), rounding=ROUND_HALF_UP))
    except InvalidOperation as exc:
        raise ValueError('Nieprawidłowa odpowiedź lokalizacji') from exc


def normalize_results(rows):
    if not isinstance(rows, list) or len(rows) > 5:
        raise ValueError('Nieprawidłowa odpowiedź lokalizacji')
    results = []
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError('Nieprawidłowa odpowiedź lokalizacji')
        label = row.get('display_name')
        if not isinstance(label, str) or not 1 <= len(label) <= 500 or any(ord(c) < 32 for c in label):
            raise ValueError('Nieprawidłowa odpowiedź lokalizacji')
        results.append({'label': label,
                        'latitude_e6': microdegrees(row.get('lat'), 90),
                        'longitude_e6': microdegrees(row.get('lon'), 180),
                        'notice': 'Punkt orientacyjny z danych mapowych; sprawdź wybrane miejsce.'})
    return results


async def lookup(query, url, *, transport=None):
    params = {'city': query.city, 'countrycodes': 'pl', 'format': 'jsonv2',
              'limit': '5', 'accept-language': 'pl'}
    if query.street:
        params['street'] = query.street
    if query.postal_code:
        params['postalcode'] = query.postal_code
    async with httpx.AsyncClient(timeout=5, follow_redirects=False, trust_env=False,
                                 transport=transport) as client:
        async with client.stream('GET', url, params=params,
                                 headers={'User-Agent': 'WiejskaPaka-AddressSearch/1.0'}) as response:
            response.raise_for_status()
            body = bytearray()
            async for chunk in response.aiter_bytes():
                body.extend(chunk)
                if len(body) > 65536:
                    raise ValueError('Zbyt duża odpowiedź lokalizacji')
    return normalize_results(json.loads(body))


@router.get('/address-search/config')
def address_search_config():
    try:
        enabled = provider_url() is not None
    except ValueError:
        enabled = False
    return JSONResponse({'enabled': enabled}, headers={'Cache-Control': 'no-store'})


@router.post('/address-search')
async def search_address(query: AddressQuery):
    try:
        url = provider_url()
        if url is None:
            raise HTTPException(503, 'Wyszukiwanie adresów nie jest jeszcze skonfigurowane')
        items = await lookup(query, url)
    except (ValueError, httpx.HTTPError, httpx.InvalidURL):
        # Never expose an upstream URL/query/address in error details.
        raise HTTPException(503, 'Wyszukiwanie adresów jest chwilowo niedostępne') from None
    return JSONResponse({'items': items, 'attribution': '© OpenStreetMap contributors'},
                        headers={'Cache-Control': 'no-store'})

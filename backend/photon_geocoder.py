"""Photon GeoJSON adapter and conservative single-process public-demo budget."""
from collections import deque
from decimal import Decimal
import json
import math
import ssl
import threading
import time
from urllib.parse import urlsplit
import httpx
from backend.address_search import microdegrees

PUBLIC_URL='https://photon.komoot.io/api/'


def is_public(url):
    return (urlsplit(url).hostname or '').lower().rstrip('.')=='photon.komoot.io'


class PublicBudget:
    """For a single-worker demo: at most 1 request/s and 120 requests/hour.

    Production/multiple-worker installations should use their own Photon service.
    Stores timestamps only, never searches, coordinates, account IDs or addresses.
    """
    def __init__(self):
        self.timestamps=deque()
        self.lock=threading.Lock()

    def reserve(self, *, now=None):
        now=time.monotonic() if now is None else now
        with self.lock:
            while self.timestamps and self.timestamps[0]<=now-3600:
                self.timestamps.popleft()
            wait=0
            if self.timestamps:
                wait=max(wait,self.timestamps[-1]+1-now)
            if len(self.timestamps)>=120:
                wait=max(wait,self.timestamps[0]+3600-now)
            if wait>0:
                return max(1,math.ceil(wait))
            self.timestamps.append(now)
            return 0


public_budget=PublicBudget()


def normalize(data):
    if not isinstance(data,dict) or data.get('type')!='FeatureCollection':
        raise ValueError('Nieprawidłowa odpowiedź geokodera')
    features=data.get('features')
    if not isinstance(features,list) or len(features)>5:
        raise ValueError('Nieprawidłowa liczba wyników')
    result=[]
    for feature in features:
        if not isinstance(feature,dict) or feature.get('type')!='Feature':
            raise ValueError('Nieprawidłowy wynik geokodera')
        props=feature.get('properties');geometry=feature.get('geometry')
        if not isinstance(props,dict) or not isinstance(geometry,dict) or geometry.get('type')!='Point':
            raise ValueError('Nieprawidłowy punkt geokodera')
        if props.get('countrycode') not in ('PL','pl'):
            continue
        coords=geometry.get('coordinates')
        if not isinstance(coords,list) or len(coords)!=2 or any(isinstance(n,bool) or not isinstance(n,(int,float,Decimal)) for n in coords):
            raise ValueError('Nieprawidłowe współrzędne geokodera')
        def text(key):
            value=props.get(key)
            if value is None:return ''
            if not isinstance(value,str) or len(value)>200 or any(ord(c)<32 for c in value):
                raise ValueError('Nieprawidłowy opis adresu')
            return value.strip()
        components=[text('name'),' '.join(filter(None,(text('street'),text('housenumber')))),
                    ' '.join(filter(None,(text('postcode'),text('city') or text('locality')))),
                    text('state'),text('country')]
        unique=[]
        for part in components:
            if part and part.casefold() not in {p.casefold() for p in unique}:
                unique.append(part)
        label=', '.join(unique)
        if not label or len(label)>500:
            raise ValueError('Nieprawidłowy opis adresu')
        result.append({'label':label,'latitude_e6':microdegrees(str(coords[1]),90),
                       'longitude_e6':microdegrees(str(coords[0]),180),
                       'notice':'Punkt orientacyjny z danych OpenStreetMap (Photon); sprawdź wybrane miejsce.'})
    return result


async def lookup(query,url,*,transport=None):
    params={'q':', '.join(filter(None,(query.street,query.postal_code,query.city))),
            'countrycode':'PL','lang':'default','limit':'5'}
    # Supported proxy/trust settings are needed for cloud egress. No account
    # bearer token or user-provided URL is accepted or forwarded by this adapter.
    try:
        context=ssl.create_default_context()
    except (OSError,ssl.SSLError):
        raise ValueError('Nie można skonfigurować zaufanych certyfikatów geokodera') from None
    async with httpx.AsyncClient(timeout=5,follow_redirects=False,trust_env=True,transport=transport,verify=context) as client:
        async with client.stream('GET',url,params=params,headers={'User-Agent':'WiejskaPaka-AddressSearch/1.0','Accept':'application/json'}) as response:
            response.raise_for_status()
            body=bytearray()
            async for chunk in response.aiter_bytes():
                body.extend(chunk)
                if len(body)>65536:
                    raise ValueError('Zbyt duża odpowiedź geokodera')
    return normalize(json.loads(body,parse_float=Decimal))

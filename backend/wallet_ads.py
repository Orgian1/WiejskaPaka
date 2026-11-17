"""Wallet-entry advertisements. Independent of every financial table.

One account row lock serializes claims across processes/devices. Server-issued
impressions and unique entry keys make counting idempotent; clicks are boolean.
"""
import base64
import binascii
import secrets
from datetime import datetime, timezone
from typing import Literal
from urllib.parse import urlsplit

from fastapi import Depends, Header, HTTPException, Query
from pydantic import BaseModel, Field, field_validator, model_validator
from backend.order_mail_outbox import _postgres
from backend.user_photos import compress_photo

SCHEMA_SQLITE = '''
CREATE TABLE IF NOT EXISTS wallet_ads (
 id TEXT PRIMARY KEY, advertiser TEXT NOT NULL, url TEXT NOT NULL,
 image TEXT NOT NULL, starts_at BIGINT NOT NULL, ends_at BIGINT NOT NULL,
 enabled INTEGER NOT NULL CHECK(enabled IN (0,1)), sort_order INTEGER NOT NULL,
 audience TEXT NOT NULL DEFAULT 'both' CHECK(audience IN ('klient','rolnik','both')),
 deleted INTEGER NOT NULL DEFAULT 0 CHECK(deleted IN (0,1)), CHECK(ends_at>starts_at)
);
CREATE TABLE IF NOT EXISTS wallet_ad_accounts (
 user_id BIGINT NOT NULL PRIMARY KEY REFERENCES users(id), last_shown BIGINT NOT NULL DEFAULT 0,
 last_ad_id TEXT REFERENCES wallet_ads(id)
);
CREATE TABLE IF NOT EXISTS wallet_ad_impressions (
 id TEXT PRIMARY KEY, user_id BIGINT NOT NULL REFERENCES users(id),
 ad_id TEXT NOT NULL REFERENCES wallet_ads(id), request_key TEXT NOT NULL,
 created_at BIGINT NOT NULL, clicked INTEGER NOT NULL DEFAULT 0 CHECK(clicked IN (0,1)),
 UNIQUE(user_id,request_key)
);
CREATE INDEX IF NOT EXISTS wallet_ad_stats ON wallet_ad_impressions(ad_id);
'''


class Campaign(BaseModel):
    model_config = {'extra': 'forbid'}
    advertiser: str = Field(min_length=1, max_length=120)
    url: str = Field(max_length=2048)
    image_base64: str | None = Field(default=None, max_length=1_400_000, repr=False)
    starts_at: datetime
    ends_at: datetime
    enabled: bool = False
    sort_order: int = Field(default=0, strict=True, ge=0, le=100000)
    audience: Literal['klient', 'rolnik', 'both'] = 'both'

    @field_validator('advertiser')
    @classmethod
    def name(cls, value):
        value = value.strip()
        if not value or any(ord(c)<32 for c in value):
            raise ValueError('Nieprawidłowa nazwa reklamodawcy')
        return value

    @field_validator('url')
    @classmethod
    def link(cls, value):
        try:
            parsed = urlsplit(value)
            if (parsed.scheme not in ('https', 'http') or not parsed.hostname
                    or parsed.username is not None or parsed.password is not None
                    or any(ord(c)<=32 or ord(c)==127 for c in value) or '\\' in value):
                raise ValueError()
            parsed.port
            parsed.hostname.encode('idna')
        except (ValueError, UnicodeError):
            raise ValueError('Podaj poprawny adres HTTP lub HTTPS bez danych logowania') from None
        return parsed._replace(scheme=parsed.scheme.lower()).geturl()

    @model_validator(mode='after')
    def dates(self):
        if (self.starts_at.tzinfo is None or self.ends_at.tzinfo is None
                or self.starts_at.microsecond or self.ends_at.microsecond
                or self.ends_at <= self.starts_at):
            raise ValueError('Podaj daty ze strefą i dokładnością do sekund; koniec musi być po początku')
        return self


class Claim(BaseModel):
    model_config = {'extra': 'forbid'}
    request_key: str = Field(pattern=r'^[A-Za-z0-9_-]{12,100}$')


def image_data(value):
    try:
        raw = base64.b64decode(value, validate=True)
    except (ValueError, binascii.Error):
        raise HTTPException(422, 'Nieprawidłowe zdjęcie') from None
    if len(raw)>1_000_000:
        raise HTTPException(413, 'Zdjęcie może mieć najwyżej 1 MB')
    clean, _, _ = compress_photo(raw, max_bytes=500_000)
    return 'data:image/jpeg;base64,' + base64.b64encode(clean).decode('ascii')


def database_now(con):
    sql = ('SELECT CAST(FLOOR(EXTRACT(EPOCH FROM clock_timestamp())) AS BIGINT) AS now'
           if _postgres(con) else "SELECT CAST(strftime('%s','now') AS INTEGER) AS now")
    return con.execute(sql).fetchone()['now']


def claim_ad(con, user_id, key, role):
    con.execute('INSERT INTO wallet_ad_accounts(user_id) VALUES(?) ON CONFLICT(user_id) DO NOTHING', (user_id,))
    suffix = ' FOR UPDATE' if _postgres(con) else ''
    account = con.execute('SELECT * FROM wallet_ad_accounts WHERE user_id=?' + suffix, (user_id,)).fetchone()
    now = database_now(con)
    # Never return a previously served creative on a retried entry request.
    if now-account['last_shown'] < 1800 or con.execute(
            'SELECT id FROM wallet_ad_impressions WHERE user_id=? AND request_key=?', (user_id, key)).fetchone():
        return {'ad': None}
    campaigns = con.execute('SELECT id FROM wallet_ads WHERE enabled=1 AND deleted=0 AND starts_at<=? AND ends_at>? AND audience IN (?, \'both\') ORDER BY sort_order,id', (now, now, role)).fetchall()
    if not campaigns:
        return {'ad': None}
    ids = [row['id'] for row in campaigns]
    index = (ids.index(account['last_ad_id'])+1)%len(ids) if account['last_ad_id'] in ids else 0
    ad = con.execute('SELECT * FROM wallet_ads WHERE id=?', (campaigns[index]['id'],)).fetchone()
    impression = secrets.token_hex(16)
    con.execute('INSERT INTO wallet_ad_impressions(id,user_id,ad_id,request_key,created_at) VALUES(?,?,?,?,?)', (impression, user_id, ad['id'], key, now))
    con.execute('UPDATE wallet_ad_accounts SET last_shown=?,last_ad_id=? WHERE user_id=?', (now, ad['id'], user_id))
    return {'ad': {'id': ad['id'], 'impression_id': impression, 'advertiser': ad['advertiser'], 'url': ad['url'], 'image': ad['image'], 'duration_seconds': 5}}


def install(app, db, write_db, current_user, database_url):
    if not database_url:
        with db() as con:
            con.executescript(SCHEMA_SQLITE)
            columns = {row['name'] for row in con.execute('PRAGMA table_info(wallet_ads)')}
            if 'audience' not in columns:
                con.execute("ALTER TABLE wallet_ads ADD COLUMN audience TEXT NOT NULL DEFAULT 'both' CHECK(audience IN ('klient','rolnik','both'))")

    def admin(user):
        if user['role'] != 'admin':
            raise HTTPException(403, 'Brak uprawnień')

    @app.post('/wallet/ads/claim')
    def claim(payload: Claim, authorization: str = Header(default=''), user=Depends(current_user)):
        with write_db(user, authorization, ('klient', 'rolnik')) as con:
            return claim_ad(con, user['id'], payload.request_key, user['role'])

    @app.post('/wallet/ads/impressions/{impression_id}/click')
    def click(impression_id: str, authorization: str = Header(default=''), user=Depends(current_user)):
        with write_db(user, authorization, ('klient', 'rolnik')) as con:
            row = con.execute('SELECT id FROM wallet_ad_impressions WHERE id=? AND user_id=?', (impression_id, user['id'])).fetchone()
            if not row:
                raise HTTPException(404, 'Nie znaleziono emisji')
            con.execute('UPDATE wallet_ad_impressions SET clicked=1 WHERE id=? AND user_id=? AND clicked=0', (impression_id, user['id']))
        return {'ok': True}

    @app.get('/admin/wallet-ads')
    def listing(limit: int = Query(default=10, ge=1, le=20), offset: int = Query(default=0, ge=0, le=100000), authorization: str = Header(default=''), user=Depends(current_user)):
        admin(user)
        with write_db(user, authorization, ('admin',)) as con:
            rows = con.execute('''SELECT a.*, (SELECT COUNT(*) FROM wallet_ad_impressions i WHERE i.ad_id=a.id) AS impressions,
             (SELECT COUNT(*) FROM wallet_ad_impressions i WHERE i.ad_id=a.id AND i.clicked=1) AS clicks
             FROM wallet_ads a WHERE a.deleted=0 ORDER BY a.sort_order,a.id LIMIT ? OFFSET ?''', (limit, offset)).fetchall()
        return {'items': [dict(row) for row in rows]}

    def save(payload, ad_id, user, authorization, creating=False):
        admin(user)
        image = image_data(payload.image_base64) if payload.image_base64 is not None else None
        if creating and image is None:
            raise HTTPException(422, 'Dodaj zdjęcie banera')
        with write_db(user, authorization, ('admin',)) as con:
            if not creating:
                row = con.execute('SELECT image FROM wallet_ads WHERE id=? AND deleted=0', (ad_id,)).fetchone()
                if not row:
                    raise HTTPException(404, 'Nie znaleziono reklamy')
                image = image or row['image']
            values = (payload.advertiser, payload.url, image, int(payload.starts_at.timestamp()), int(payload.ends_at.timestamp()), int(payload.enabled), payload.sort_order, payload.audience)
            if creating and payload.enabled and payload.url != 'https://example.invalid/wiejskapaka-demo-placeholder-' + payload.audience:
                # Retire temporary demo artwork when a real campaign is activated
                # for the same audience. Never touch other campaigns.
                con.execute("""UPDATE wallet_ads SET enabled=0,deleted=1
                    WHERE audience=? AND url=? AND advertiser=?""",
                    (payload.audience,
                     'https://example.invalid/wiejskapaka-demo-placeholder-' + payload.audience,
                     'WiejskaPaka - miejsce na reklamę'))
            if creating:
                con.execute('INSERT INTO wallet_ads(advertiser,url,image,starts_at,ends_at,enabled,sort_order,audience,id) VALUES(?,?,?,?,?,?,?,?,?)', (*values, ad_id))
            else:
                con.execute('UPDATE wallet_ads SET advertiser=?,url=?,image=?,starts_at=?,ends_at=?,enabled=?,sort_order=?,audience=? WHERE id=? AND deleted=0', (*values, ad_id))
        return {'id': ad_id}

    @app.post('/admin/wallet-ads', status_code=201)
    def create(payload: Campaign, authorization: str = Header(default=''), user=Depends(current_user)):
        return save(payload, secrets.token_hex(16), user, authorization, True)

    @app.put('/admin/wallet-ads/{ad_id}')
    def update(ad_id: str, payload: Campaign, authorization: str = Header(default=''), user=Depends(current_user)):
        return save(payload, ad_id, user, authorization)

    @app.delete('/admin/wallet-ads/{ad_id}')
    def delete(ad_id: str, authorization: str = Header(default=''), user=Depends(current_user)):
        admin(user)
        with write_db(user, authorization, ('admin',)) as con:
            con.execute('UPDATE wallet_ads SET deleted=1,enabled=0 WHERE id=?', (ad_id,))
        return {'ok': True}

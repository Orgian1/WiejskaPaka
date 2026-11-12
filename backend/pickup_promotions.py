"""Three-point promotional entitlements, never a payment or automatic future charge."""
from datetime import date, datetime
from uuid import uuid4
from zoneinfo import ZoneInfo
from fastapi import Depends, Header, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator

SCHEMA = '''
CREATE TABLE IF NOT EXISTS pickup_promo_codes (
 code TEXT PRIMARY KEY,
 expires_on TEXT NOT NULL,
 max_redemptions INTEGER NOT NULL CHECK(max_redemptions BETWEEN 1 AND 1000000),
 redemption_count INTEGER NOT NULL DEFAULT 0 CHECK(redemption_count>=0 AND redemption_count<=max_redemptions),
 active INTEGER NOT NULL CHECK(active IN (0,1))
);
CREATE TABLE IF NOT EXISTS pickup_promo_grants (
 id TEXT PRIMARY KEY,
 user_id INTEGER NOT NULL REFERENCES users(id),
 code TEXT NOT NULL REFERENCES pickup_promo_codes(code),
 expires_on TEXT NOT NULL,
 remaining INTEGER NOT NULL CHECK(remaining BETWEEN 0 AND 3),
 UNIQUE(user_id,code)
);
CREATE TABLE IF NOT EXISTS pickup_promo_points (
 point_id INTEGER PRIMARY KEY REFERENCES pickup_points(id),
 grant_id TEXT NOT NULL REFERENCES pickup_promo_grants(id)
);
CREATE INDEX IF NOT EXISTS pickup_promo_grants_user_idx ON pickup_promo_grants(user_id,expires_on);
'''


def business_today():
    return datetime.now(ZoneInfo('Europe/Warsaw')).date()


class CodeIn(BaseModel):
    model_config = ConfigDict(extra='forbid')
    code: str = Field(min_length=4, max_length=40)

    @field_validator('code')
    @classmethod
    def canonical_code(cls, value):
        value=value.strip().upper()
        if not 4 <= len(value) <= 40 or any(c not in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-' for c in value):
            raise ValueError('Kod: 4–40 liter, cyfr lub znaków -')
        return value


class PromoSettings(BaseModel):
    model_config = ConfigDict(extra='forbid')
    expires_on: date
    max_redemptions: int = Field(strict=True, ge=1, le=1000000)
    active: bool = Field(strict=True, default=True)

    @field_validator('expires_on')
    @classmethod
    def supported_date(cls, value):
        if not 2000 <= value.year <= 2100:
            raise ValueError('Data musi być pomiędzy rokiem 2000 a 2100')
        return value


class PromoCreate(CodeIn, PromoSettings):
    pass


def grant_reply(row, *, today=None):
    today=(today or business_today()).isoformat()
    return {'code':row['code'],'expires_on':row['expires_on'],
            'remaining':row['remaining'] if row['expires_on']>=today else 0,
            'granted_points':3}


def consume_for_point(con, user_id, point_id, *, postgres=False, today=None):
    """Same transaction as point creation. Lock account before examining grants."""
    suffix=' FOR UPDATE' if postgres else ''
    con.execute('SELECT id FROM users WHERE id=?'+suffix,(user_id,)).fetchone()
    row=con.execute('''SELECT id,expires_on FROM pickup_promo_grants
        WHERE user_id=? AND remaining>0 AND expires_on>=? ORDER BY expires_on,id LIMIT 1'''+suffix,
        (user_id,(today or business_today()).isoformat())).fetchone()
    if row is None:
        return None
    changed=con.execute('UPDATE pickup_promo_grants SET remaining=remaining-1 WHERE id=? AND remaining>0',(row['id'],))
    if changed.rowcount!=1:
        raise HTTPException(409,'Uprawnienie promocyjne zmieniło się; odśwież punkty')
    con.execute('INSERT INTO pickup_promo_points(point_id,grant_id) VALUES(?,?)',(point_id,row['id']))
    return {'free_until':row['expires_on'],'charges_executed':False}


def point_terms(con, point_id):
    row=con.execute('''SELECT g.expires_on FROM pickup_promo_points p
        JOIN pickup_promo_grants g ON g.id=p.grant_id WHERE p.point_id=?''',(point_id,)).fetchone()
    return {'free_until':row['expires_on']} if row else None


def install(app, db, write_db, current_user, database_url):
    if not database_url:
        with db() as con:
            con.executescript(SCHEMA)

    @app.get('/admin/pickup-promotions')
    def list_codes(user=Depends(current_user), authorization: str | None=Header(default=None)):
        with write_db(user,authorization,('admin',)) as con:
            return {'items':[dict(r) for r in con.execute('SELECT * FROM pickup_promo_codes ORDER BY code LIMIT 1000')]}

    @app.post('/admin/pickup-promotions',status_code=201)
    def create_code(payload: PromoCreate, user=Depends(current_user), authorization: str | None=Header(default=None)):
        with write_db(user,authorization,('admin',)) as con:
            # Conditional INSERT handles concurrent administrators on either DB.
            changed=con.execute('''INSERT INTO pickup_promo_codes(code,expires_on,max_redemptions,active)
                VALUES(?,?,?,?) ON CONFLICT(code) DO NOTHING''',
                (payload.code,payload.expires_on.isoformat(),payload.max_redemptions,int(payload.active)))
            if changed.rowcount!=1:
                raise HTTPException(409,'Kod już istnieje; edytuj jego ustawienia')
        return {'code':payload.code,'granted_points':3}

    @app.put('/admin/pickup-promotions/{code}')
    def update_code(code: str, payload: PromoSettings, user=Depends(current_user), authorization: str | None=Header(default=None)):
        try:
            key=CodeIn(code=code).code
        except ValueError:
            raise HTTPException(422,'Nieprawidłowy kod') from None
        with write_db(user,authorization,('admin',)) as con:
            row=con.execute('SELECT redemption_count FROM pickup_promo_codes WHERE code=?'+(' FOR UPDATE' if database_url else ''),(key,)).fetchone()
            if row is None:
                raise HTTPException(404,'Brak kodu')
            if payload.max_redemptions<row['redemption_count']:
                raise HTTPException(409,'Limit nie może być niższy niż liczba wykorzystań')
            con.execute('UPDATE pickup_promo_codes SET expires_on=?,max_redemptions=?,active=? WHERE code=?',
                        (payload.expires_on.isoformat(),payload.max_redemptions,int(payload.active),key))
        return {'saved':True,'existing_grants_unchanged':True}

    @app.get('/farmers/me/pickup-promotions')
    def my_grants(user=Depends(current_user), authorization: str | None=Header(default=None)):
        with write_db(user,authorization,('rolnik',)) as con:
            rows=con.execute('SELECT code,expires_on,remaining FROM pickup_promo_grants WHERE user_id=? ORDER BY expires_on,code',(user['id'],)).fetchall()
            items=[grant_reply(r) for r in rows]
            return {'items':items,'available_points':sum(r['remaining'] for r in items)}

    @app.post('/farmers/me/pickup-promotions/redeem')
    def redeem(payload: CodeIn, user=Depends(current_user), authorization: str | None=Header(default=None)):
        with write_db(user,authorization,('rolnik',)) as con:
            suffix=' FOR UPDATE' if database_url else ''
            con.execute('SELECT id FROM users WHERE id=?'+suffix,(user['id'],)).fetchone()
            existing=con.execute('SELECT code,expires_on,remaining FROM pickup_promo_grants WHERE user_id=? AND code=?',(user['id'],payload.code)).fetchone()
            if existing is not None:
                result=grant_reply(existing);status=200
            else:
                code=con.execute('SELECT * FROM pickup_promo_codes WHERE code=?'+suffix,(payload.code,)).fetchone()
                if code is None or not code['active'] or code['expires_on']<business_today().isoformat() or code['redemption_count']>=code['max_redemptions']:
                    raise HTTPException(409,'Kod jest niedostępny, wygasł lub osiągnął limit')
                con.execute('INSERT INTO pickup_promo_grants(id,user_id,code,expires_on,remaining) VALUES(?,?,?,?,3)',
                            (uuid4().hex,user['id'],payload.code,code['expires_on']))
                con.execute('UPDATE pickup_promo_codes SET redemption_count=redemption_count+1 WHERE code=?',(payload.code,))
                result=grant_reply({'code':payload.code,'expires_on':code['expires_on'],'remaining':3});status=201
        return JSONResponse(status_code=status,content=result)

"""A dated seller entitlement, independent of wallets and order fulfilment."""
from datetime import datetime
import os
import time
from zoneinfo import ZoneInfo

from fastapi import Depends, Header, HTTPException
from pydantic import BaseModel, Field

CAMPAIGN = 'wiejskapaka-december-2026'
CODE = 'WIEJSKAPAKA'
POINT_LIMIT = 3
ENDS_AT = '2027-01-01T00:00:00+01:00'  # Exclusive, Europe/Warsaw.
EXPIRES_AT = int(datetime(2027, 1, 1, tzinfo=ZoneInfo('Europe/Warsaw')).timestamp())
SCHEMA_SQLITE = '''
CREATE TABLE IF NOT EXISTS pickup_promotion_grants (
 farmer_id INTEGER NOT NULL REFERENCES users(id), campaign TEXT NOT NULL,
 redeemed_at INTEGER NOT NULL, expires_at INTEGER NOT NULL,
 point_limit INTEGER NOT NULL CHECK(point_limit=3),
 PRIMARY KEY(farmer_id,campaign), CHECK(redeemed_at<expires_at)
);
'''


def enabled():
    return os.environ.get('WP_ENABLE_PICKUP_PROMOTION') == '1'


def now_epoch():
    return int(time.time())


def overview(con, farmer_id, *, now=None):
    now = now_epoch() if now is None else now
    grant = con.execute('SELECT redeemed_at,expires_at FROM pickup_promotion_grants WHERE farmer_id=? AND campaign=?',
                        (farmer_id, CAMPAIGN)).fetchone()
    expiry = min(grant['expires_at'], EXPIRES_AT) if grant else EXPIRES_AT
    active = grant is not None and now < expiry
    # The same ordered selection is used for every read: at most three active places,
    # never three dates or three new points on each redemption.
    points = con.execute('SELECT id FROM pickup_points WHERE farmer_id=? AND active=1 ORDER BY id LIMIT 3',
                         (farmer_id,)).fetchall() if active else []
    return {'enabled': True, 'campaign': CAMPAIGN, 'redeemed': grant is not None,
            'active': active, 'expired': now >= expiry, 'point_limit': POINT_LIMIT,
            'ends_at': ENDS_AT, 'valid_through': '2026-12-31',
            'covered_point_ids': [p['id'] for p in points],
            'remaining': POINT_LIMIT-len(points) if active else 0}


class RedeemIn(BaseModel):
    model_config = {'extra': 'forbid'}
    code: str = Field(min_length=1, max_length=40, strict=True)


def register(app, account_session_db, current_user):
    @app.get('/farmers/me/pickup-promotion')
    def pickup_promotion_status(user=Depends(current_user), authorization: str | None = Header(default=None)):
        with account_session_db(user, authorization) as con:
            if user['role'] != 'rolnik':
                raise HTTPException(403, 'Promocja jest dostępna dla sprzedawców')
            return overview(con, user['id']) if enabled() else {'enabled': False}

    @app.post('/farmers/me/pickup-promotion')
    def redeem_pickup_promotion(payload: RedeemIn, user=Depends(current_user), authorization: str | None = Header(default=None)):
        with account_session_db(user, authorization) as con:
            if user['role'] != 'rolnik':
                raise HTTPException(403, 'Promocja jest dostępna dla sprzedawców')
            if not enabled():
                raise HTTPException(503, 'Promocja nie jest włączona')
            if payload.code.strip().replace(' ', '').upper() != CODE:
                raise HTTPException(422, 'Nieprawidłowy kod promocyjny')
            now = now_epoch()
            if now >= EXPIRES_AT:
                raise HTTPException(410, 'Promocja zakończyła się 31 grudnia 2026 r.')
            con.execute('''INSERT INTO pickup_promotion_grants(farmer_id,campaign,redeemed_at,expires_at,point_limit)
                           VALUES(?,?,?,?,?) ON CONFLICT(farmer_id,campaign) DO NOTHING''',
                        (user['id'], CAMPAIGN, now, EXPIRES_AT, POINT_LIMIT))
            return overview(con, user['id'], now=now)

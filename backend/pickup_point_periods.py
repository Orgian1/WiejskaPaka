"""Thirty-day pickup point entitlement ledger. Does not authorize or simulate wallet debits.

A point is paid only after a separate verified wallet debit is recorded.
"""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from backend.pickup_point_pricing import POINT_MONTHLY_PRICE_GROSZE

SCHEMA = """
CREATE TABLE IF NOT EXISTS pickup_point_periods (
 id TEXT PRIMARY KEY,
 point_id INTEGER NOT NULL REFERENCES pickup_points(id),
 farmer_id INTEGER NOT NULL REFERENCES users(id),
 starts_at TEXT NOT NULL,
 ends_at TEXT NOT NULL,
 price_grosze INTEGER NOT NULL CHECK(price_grosze IN (0,1000)),
 kind TEXT NOT NULL CHECK(kind IN ('promotion','wallet_test')),
 wallet_entry_id TEXT,
 CHECK((kind='promotion' AND price_grosze=0 AND wallet_entry_id IS NULL)
    OR (kind='wallet_test' AND price_grosze=1000 AND wallet_entry_id IS NOT NULL)),
 UNIQUE(point_id,starts_at),
 UNIQUE(wallet_entry_id)
);
CREATE INDEX IF NOT EXISTS pickup_point_periods_active_idx
 ON pickup_point_periods(point_id,ends_at);
"""

def now_warsaw():
    return datetime.now(ZoneInfo('Europe/Warsaw'))

def period_end(start):
    if start.tzinfo is None:
        raise ValueError('Start requires timezone')
    return start + timedelta(days=30)

def active_period(con, point_id, *, now=None):
    now=now or now_warsaw()
    row=con.execute("""SELECT kind,starts_at,ends_at,price_grosze
        FROM pickup_point_periods WHERE point_id=?
        AND starts_at<=? AND ends_at>? ORDER BY ends_at DESC LIMIT 1""",
        (point_id,now.isoformat(),now.isoformat())).fetchone()
    return dict(row) if row else None

def quote():
    return {'price_grosze':POINT_MONTHLY_PRICE_GROSZE,'period_days':30,
            'wallet_charge_available':False}

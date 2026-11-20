"""Thirty-day pickup point entitlement ledger. Does not authorize or simulate wallet debits.

A point is paid only after a separate verified wallet debit is recorded.
"""
from datetime import datetime, timedelta, timezone
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
    return (start.astimezone(timezone.utc) + timedelta(days=30)).astimezone(ZoneInfo('Europe/Warsaw'))

def active_period(con, point_id, *, now=None):
    now=now or now_warsaw()
    # ISO strings with different UTC offsets do not sort chronologically.
    # Compare instants in Python to remain correct across DST transitions.
    rows=con.execute("""SELECT kind,starts_at,ends_at,price_grosze
        FROM pickup_point_periods WHERE point_id=?""",(point_id,)).fetchall()
    now_utc=now.astimezone(timezone.utc)
    valid=[r for r in rows if datetime.fromisoformat(r['starts_at']).astimezone(timezone.utc)<=now_utc
           <datetime.fromisoformat(r['ends_at']).astimezone(timezone.utc)]
    return dict(max(valid,key=lambda r:datetime.fromisoformat(r['ends_at']).astimezone(timezone.utc))) if valid else None

def quote():
    return {'price_grosze':POINT_MONTHLY_PRICE_GROSZE,'period_days':30,
            'wallet_charge_available':False}


def point_status(con, point_id, *, now=None):
    """Single read-only source of truth for the point's paid/free access window."""
    period=active_period(con,point_id,now=now)
    return {'point_id':point_id,'entitled':period is not None,
            'period':period,'renewal':quote()}


def point_is_entitled(con, point_id, *, now=None, allow_unrecorded=False):
    if getattr(con, 'gateway', False):
        row = con.execute('SELECT wp_rls.pickup_point_entitled(?,?::timestamptz,?) AS entitled',
                          (point_id, (now or now_warsaw()).isoformat(), allow_unrecorded)).fetchone()
        return row['entitled']
    if active_period(con, point_id, now=now) is not None:
        return True
    # Direct orders historically accepted points that had never had a ledger period.
    return allow_unrecorded and con.execute(
        'SELECT 1 FROM pickup_point_periods WHERE point_id=? LIMIT 1', (point_id,)
    ).fetchone() is None


def entitled_point_ids(con, point_ids, *, now=None):
    """Read-only entitlement filter; empty input never issues a broad query."""
    ids=tuple(dict.fromkeys(point_ids))
    return {point_id for point_id in ids if point_is_entitled(con,point_id,now=now)}

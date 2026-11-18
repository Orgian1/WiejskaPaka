-- PostgreSQL migration: 30-day pickup point entitlement ledger.
-- Apply only after backup, before deploying code that creates promotional points.
BEGIN;
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
CREATE INDEX IF NOT EXISTS pickup_point_periods_active_idx ON pickup_point_periods(point_id,ends_at);
COMMIT;

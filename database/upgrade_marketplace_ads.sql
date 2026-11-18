-- Apply to PostgreSQL before starting the app version with marketplace advertising.
CREATE TABLE IF NOT EXISTS marketplace_ad_campaigns (
 id TEXT PRIMARY KEY,
 slot TEXT NOT NULL CHECK(slot IN ('login','buyer','seller')),
 title TEXT NOT NULL,
 body TEXT NOT NULL,
 enabled INTEGER NOT NULL DEFAULT 0 CHECK(enabled IN (0,1)),
 starts_at BIGINT NOT NULL,
 ends_at BIGINT NOT NULL,
 CHECK(ends_at>starts_at)
);
CREATE INDEX IF NOT EXISTS marketplace_ad_active_idx
 ON marketplace_ad_campaigns(slot,enabled,starts_at,ends_at);

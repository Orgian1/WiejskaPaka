-- Wallet ads: no financial tables or balances are modified.

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

-- Run once in a transaction on PostgreSQL, after previous upgrades.
CREATE TABLE IF NOT EXISTS payment_simulations (
 order_id BIGINT PRIMARY KEY REFERENCES orders(id),
 total_grosze BIGINT NOT NULL CHECK(total_grosze>0),
 products_grosze BIGINT NOT NULL CHECK(products_grosze>=0),
 delivery_grosze BIGINT NOT NULL CHECK(delivery_grosze>=0),
 commission_grosze BIGINT NOT NULL CHECK(commission_grosze>=0),
 seller_grosze BIGINT NOT NULL CHECK(seller_grosze>=0),
 state TEXT NOT NULL,
 refund_grosze BIGINT NOT NULL DEFAULT 0 CHECK(refund_grosze>=0),
 payout_grosze BIGINT NOT NULL DEFAULT 0 CHECK(payout_grosze>=0),
 CHECK(total_grosze=products_grosze+delivery_grosze),
 CHECK(total_grosze=commission_grosze+seller_grosze)
);
CREATE TABLE IF NOT EXISTS payment_simulation_events (
 event_id TEXT PRIMARY KEY,
 order_id BIGINT NOT NULL REFERENCES payment_simulations(order_id),
 event_type TEXT NOT NULL,
 state_after TEXT NOT NULL,
 created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS payment_events_order_idx ON payment_simulation_events(order_id,created_at);

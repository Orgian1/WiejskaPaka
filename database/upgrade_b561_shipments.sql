-- Apply manually after backup; test database only. Existing orders are not backfilled.
BEGIN;
CREATE TABLE IF NOT EXISTS shipment_groups (
 id TEXT PRIMARY KEY, buyer_id BIGINT NOT NULL REFERENCES users(id),
 farmer_id BIGINT NOT NULL REFERENCES users(id),
 fulfillment TEXT NOT NULL CHECK(fulfillment IN ('odbior','dostawa')),
 delivery_grosze BIGINT NOT NULL CHECK(delivery_grosze>=0),
 created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS shipment_order_links (
 order_id BIGINT PRIMARY KEY REFERENCES orders(id),
 shipment_id TEXT NOT NULL REFERENCES shipment_groups(id)
);
CREATE INDEX IF NOT EXISTS shipment_order_links_group_idx ON shipment_order_links(shipment_id);
COMMIT;

-- Private test-only support. No payment, inventory or order status changes.

CREATE TABLE IF NOT EXISTS support_cases (
 id TEXT PRIMARY KEY, buyer_id INTEGER NOT NULL REFERENCES users(id),
 farmer_id INTEGER NOT NULL REFERENCES users(id),
 order_id INTEGER REFERENCES orders(id), shipment_id TEXT REFERENCES shipment_groups(id),
 request_id TEXT NOT NULL,
 category TEXT NOT NULL CHECK(category IN ('product','pickup','delivery','other')),
 description TEXT NOT NULL CHECK(length(description) BETWEEN 10 AND 2000),
 status TEXT NOT NULL DEFAULT 'new' CHECK(status IN ('new','in_review','closed_test')),
 revision INTEGER NOT NULL DEFAULT 1 CHECK(revision>0),
 created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
 CHECK((order_id IS NOT NULL AND shipment_id IS NULL) OR (order_id IS NULL AND shipment_id IS NOT NULL)),
 UNIQUE(buyer_id,request_id)
);
CREATE INDEX IF NOT EXISTS support_cases_buyer_idx ON support_cases(buyer_id,created_at,id);
CREATE INDEX IF NOT EXISTS support_cases_farmer_idx ON support_cases(farmer_id,created_at,id);
CREATE TABLE IF NOT EXISTS support_case_events (
 id TEXT PRIMARY KEY, case_id TEXT NOT NULL REFERENCES support_cases(id),
 actor_id INTEGER NOT NULL REFERENCES users(id),
 actor_role TEXT NOT NULL CHECK(actor_role IN ('klient','rolnik','admin')),
 request_id TEXT NOT NULL, revision INTEGER NOT NULL CHECK(revision>0),
 message TEXT NOT NULL CHECK(length(message)<=2000),
 requested_status TEXT CHECK(requested_status IN ('in_review','closed_test')),
 status_after TEXT NOT NULL CHECK(status_after IN ('new','in_review','closed_test')),
 created_at TEXT NOT NULL,
 UNIQUE(case_id,actor_id,request_id), UNIQUE(case_id,revision)
);

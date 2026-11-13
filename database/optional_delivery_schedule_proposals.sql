-- Versioned delivery rescheduling with explicit buyer consent.
BEGIN;
CREATE TABLE delivery_schedule_proposals (
 id TEXT PRIMARY KEY,
 anchor_order_id BIGINT NOT NULL REFERENCES orders(id),
 base_revision INTEGER NOT NULL CHECK(base_revision>=0),
 request_revision INTEGER NOT NULL CHECK(request_revision=base_revision+1),
 delivery_date TEXT NOT NULL,
 from_minute INTEGER NOT NULL CHECK(from_minute>=0 AND from_minute<1440),
 to_minute INTEGER NOT NULL CHECK(to_minute>from_minute AND to_minute<=1440),
 member_ids TEXT NOT NULL,
 prior_schedule TEXT NOT NULL,
 state TEXT NOT NULL CHECK(state IN ('pending','accepted','declined','superseded')),
 created_at TEXT NOT NULL,
 decided_at TEXT,
 UNIQUE(anchor_order_id,base_revision)
);
CREATE INDEX delivery_schedule_proposals_anchor ON delivery_schedule_proposals(anchor_order_id,request_revision);

COMMIT;

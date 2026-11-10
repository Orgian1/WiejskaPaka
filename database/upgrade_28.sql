-- Etap 28. Uruchom ręcznie na PostgreSQL przed użyciem endpointu administratora.
CREATE TABLE IF NOT EXISTS payout_schedule_runs (
 payout_date TEXT PRIMARY KEY,
 created_at TEXT NOT NULL,
 farmer_count BIGINT NOT NULL CHECK(farmer_count>=0),
 plan_count BIGINT NOT NULL CHECK(plan_count>=0),
 cancelled_count BIGINT NOT NULL CHECK(cancelled_count>=0)
);

-- Apply to PostgreSQL only after backup and review, before enabling the feature.
BEGIN;
CREATE TABLE IF NOT EXISTS shipment_public_refs (
 shipment_id TEXT PRIMARY KEY REFERENCES shipment_groups(id),
 farmer_id BIGINT NOT NULL REFERENCES users(id),
 public_number TEXT NOT NULL,
 UNIQUE(farmer_id, public_number)
);
COMMIT;

-- Private per-account route order, versioned to protect changes on other devices.
BEGIN;
CREATE TABLE seller_navigation (
 user_id BIGINT PRIMARY KEY REFERENCES users(id),
 revision INTEGER NOT NULL DEFAULT 0 CHECK(revision >= 0),
 point_ids TEXT NOT NULL DEFAULT '[]'
);
COMMIT;

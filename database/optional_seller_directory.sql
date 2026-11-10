-- Public handles are opt-in. Enable WP_ENABLE_SELLER_SEARCH only after review.
BEGIN;
CREATE TABLE seller_public_logins (
 user_id BIGINT PRIMARY KEY REFERENCES users(id),
 login TEXT NOT NULL UNIQUE CHECK(login ~ '^[a-z][a-z0-9_]{2,29}$'),
 farm_name_key TEXT NOT NULL
);
COMMIT;

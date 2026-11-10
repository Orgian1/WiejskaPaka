-- Run manually on test PostgreSQL before using saved cart API.
BEGIN;
CREATE TABLE IF NOT EXISTS saved_cart_items (
 buyer_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 product_id BIGINT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
 quantity BIGINT NOT NULL CHECK(quantity BETWEEN 1 AND 1000),
 PRIMARY KEY(buyer_id,product_id)
);
COMMIT;

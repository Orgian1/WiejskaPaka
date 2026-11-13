-- Additive, reversible availability flag. No product, stock or order is changed.
CREATE TABLE IF NOT EXISTS product_listing_states(
 product_id BIGINT PRIMARY KEY REFERENCES products(id),
 active INTEGER NOT NULL DEFAULT 1 CHECK(active IN (0,1))
);

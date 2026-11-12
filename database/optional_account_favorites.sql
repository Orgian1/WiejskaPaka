-- Private per-account favorite products. No customer contact data.
BEGIN;
CREATE TABLE account_favorites (
 user_id BIGINT NOT NULL REFERENCES users(id),
 product_id BIGINT NOT NULL REFERENCES products(id),
 PRIMARY KEY(user_id, product_id)
);
CREATE TABLE account_saved_locations (
 user_id BIGINT PRIMARY KEY REFERENCES users(id),
 latitude_e6 INTEGER NOT NULL CHECK(latitude_e6 BETWEEN -90000000 AND 90000000),
 longitude_e6 INTEGER NOT NULL CHECK(longitude_e6 BETWEEN -180000000 AND 180000000)
);
COMMIT;

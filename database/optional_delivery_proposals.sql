-- Negotiated delivery times; apply after optional_address_delivery.sql.
BEGIN;

CREATE TABLE IF NOT EXISTS delivery_time_proposals (
 order_id BIGINT NOT NULL REFERENCES orders(id), revision BIGINT NOT NULL CHECK(revision>=1),
 delivery_date TEXT NOT NULL, start_minute BIGINT NOT NULL, end_minute BIGINT NOT NULL,
 state TEXT NOT NULL DEFAULT 'pending' CHECK(state IN ('pending','accepted','declined')),
 PRIMARY KEY(order_id,revision),
 CHECK(start_minute>=0 AND end_minute<=1439 AND start_minute<end_minute)
);

COMMIT;

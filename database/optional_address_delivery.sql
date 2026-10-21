-- Opt-in address delivery settings and seller acceptance. Does not change historical orders.
BEGIN;

CREATE TABLE IF NOT EXISTS seller_delivery_windows (
 id TEXT PRIMARY KEY, farmer_id BIGINT NOT NULL REFERENCES users(id),
 city TEXT NOT NULL, city_key TEXT NOT NULL, postal_code TEXT NOT NULL CHECK(length(postal_code)=6),
 weekday BIGINT NOT NULL CHECK(weekday BETWEEN 0 AND 6),
 start_minute BIGINT NOT NULL CHECK(start_minute BETWEEN 0 AND 1439),
 end_minute BIGINT NOT NULL CHECK(end_minute BETWEEN 1 AND 1440 AND end_minute>start_minute),
 active BIGINT NOT NULL DEFAULT 1 CHECK(active IN (0,1))
);
CREATE INDEX IF NOT EXISTS seller_delivery_windows_farmer ON seller_delivery_windows(farmer_id,active);
CREATE TABLE IF NOT EXISTS address_delivery_requests (
 order_id BIGINT PRIMARY KEY REFERENCES orders(id),
 window_id TEXT NOT NULL REFERENCES seller_delivery_windows(id),
 delivery_date TEXT NOT NULL,
 customer_from BIGINT NOT NULL, customer_to BIGINT NOT NULL,
 agreed_from BIGINT NOT NULL, agreed_to BIGINT NOT NULL,
 state TEXT NOT NULL DEFAULT 'pending' CHECK(state IN ('pending','accepted','declined')),
 revision BIGINT NOT NULL DEFAULT 0 CHECK(revision>=0),
 phone_sealed TEXT NOT NULL,
 CHECK(customer_from>=0 AND customer_to<=1440 AND customer_from<customer_to),
 CHECK(agreed_from>=customer_from AND agreed_to<=customer_to AND agreed_from<agreed_to)
);

COMMIT;

-- Original terms only for future checkouts; deliberately no historical backfill.
BEGIN;
CREATE TABLE IF NOT EXISTS order_purchase_records (
 order_id BIGINT PRIMARY KEY REFERENCES orders(id),
 buyer_id BIGINT NOT NULL REFERENCES users(id), farmer_id BIGINT NOT NULL REFERENCES users(id),
 product_id BIGINT NOT NULL REFERENCES products(id), pickup_code TEXT NOT NULL, product_name TEXT NOT NULL,
 unit_price_grosze BIGINT NOT NULL CHECK(unit_price_grosze>0),
 quantity BIGINT NOT NULL CHECK(quantity>0),
 subtotal_grosze BIGINT NOT NULL CHECK(subtotal_grosze=unit_price_grosze*quantity),
 delivery_grosze BIGINT NOT NULL CHECK(delivery_grosze>=0),
 total_grosze BIGINT NOT NULL CHECK(total_grosze=subtotal_grosze+delivery_grosze),
 fulfillment TEXT NOT NULL CHECK(fulfillment IN ('odbior','dostawa')),
 pickup_point_id BIGINT, point_name TEXT, point_city TEXT, point_street TEXT, point_opening_hours TEXT,
 latitude_e6 BIGINT CHECK(latitude_e6 BETWEEN -90000000 AND 90000000),
 longitude_e6 BIGINT CHECK(longitude_e6 BETWEEN -180000000 AND 180000000),
 ordered_at TEXT NOT NULL, captured_at TEXT NOT NULL, reservation_expires_at TEXT NOT NULL,
 CHECK((latitude_e6 IS NULL AND longitude_e6 IS NULL) OR (latitude_e6 IS NOT NULL AND longitude_e6 IS NOT NULL)),
 CHECK((fulfillment='odbior' AND pickup_point_id IS NOT NULL AND point_name IS NOT NULL
        AND point_city IS NOT NULL AND point_street IS NOT NULL AND point_opening_hours IS NOT NULL AND delivery_grosze=0)
    OR (fulfillment='dostawa' AND pickup_point_id IS NULL AND point_name IS NULL AND point_city IS NULL
        AND point_street IS NULL AND point_opening_hours IS NULL AND latitude_e6 IS NULL AND longitude_e6 IS NULL))
);
CREATE OR REPLACE FUNCTION reject_purchase_record_mutation() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'Purchase records are insert-only' USING ERRCODE='23000';
END;
$$;
DROP TRIGGER IF EXISTS purchase_records_no_mutation ON order_purchase_records;
CREATE TRIGGER purchase_records_no_mutation BEFORE UPDATE OR DELETE ON order_purchase_records
FOR EACH ROW EXECUTE FUNCTION reject_purchase_record_mutation();
COMMIT;

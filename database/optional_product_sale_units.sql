-- Optional feature migration. Run manually as schema owner on the test DB.
-- Does NOT reinterpret products.stock, orders.quantity, prices or old records.
-- Keep WP_ENABLE_PRODUCT_UNITS unset until this migration is verified.
BEGIN;
CREATE TABLE product_sale_units (
 product_id BIGINT PRIMARY KEY REFERENCES products(id) ON DELETE CASCADE,
 unit TEXT NOT NULL CHECK(unit IN ('szt','kg','g','l','ml','opak','peczek','sloik','butelka','worek','skrzynka','tacka')),
 content_json TEXT
);
CREATE TABLE order_sale_units (
 order_id BIGINT PRIMARY KEY REFERENCES orders(id),
 unit TEXT NOT NULL CHECK(unit IN ('szt','kg','g','l','ml','opak','peczek','sloik','butelka','worek','skrzynka','tacka')),
 content_json TEXT
);
CREATE FUNCTION wp_reject_sale_unit_change() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 RAISE EXCEPTION 'Sale unit records are insert-only';
END;
$$;
CREATE TRIGGER product_sale_units_immutable BEFORE UPDATE OR DELETE ON product_sale_units
FOR EACH ROW EXECUTE FUNCTION wp_reject_sale_unit_change();
CREATE TRIGGER order_sale_units_immutable BEFORE UPDATE OR DELETE ON order_sale_units
FOR EACH ROW EXECUTE FUNCTION wp_reject_sale_unit_change();
COMMIT;
-- Separate, explicit grant after reviewing the actual runtime role:
-- GRANT SELECT,INSERT ON product_sale_units,order_sale_units TO wp_preview_app;

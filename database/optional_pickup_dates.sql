-- Explicit test-database migration. Existing points and orders are unchanged.
BEGIN;
CREATE TABLE pickup_point_dates (
 point_id BIGINT NOT NULL REFERENCES pickup_points(id) ON DELETE CASCADE,
 attendance_date TEXT NOT NULL CHECK(attendance_date ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$'),
 PRIMARY KEY(point_id,attendance_date)
);
COMMIT;
-- GRANT SELECT,INSERT,DELETE ON public.pickup_point_dates TO wp_preview_app;

-- Local discovery only. No user location history, remote geocoder or paid service.
BEGIN;
CREATE TABLE IF NOT EXISTS pickup_point_coordinates (
    point_id BIGINT PRIMARY KEY REFERENCES pickup_points(id) ON DELETE CASCADE,
    latitude_e6 INTEGER NOT NULL CHECK(latitude_e6 BETWEEN -90000000 AND 90000000),
    longitude_e6 INTEGER NOT NULL CHECK(longitude_e6 BETWEEN -180000000 AND 180000000),
    sphere_x DOUBLE PRECISION NOT NULL CHECK(sphere_x BETWEEN -1 AND 1),
    sphere_y DOUBLE PRECISION NOT NULL CHECK(sphere_y BETWEEN -1 AND 1),
    sphere_z DOUBLE PRECISION NOT NULL CHECK(sphere_z BETWEEN -1 AND 1)
);
CREATE INDEX IF NOT EXISTS pickup_coordinates_x ON pickup_point_coordinates(sphere_x);
CREATE INDEX IF NOT EXISTS pickup_coordinates_y ON pickup_point_coordinates(sphere_y);
CREATE INDEX IF NOT EXISTS pickup_coordinates_z ON pickup_point_coordinates(sphere_z);
CREATE TABLE IF NOT EXISTS product_search_names (
    product_id BIGINT PRIMARY KEY REFERENCES products(id) ON DELETE CASCADE,
    source_name TEXT NOT NULL,
    name_key TEXT NOT NULL
);
COMMIT;

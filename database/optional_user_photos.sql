-- Optional photo storage; enable WP_ENABLE_USER_PHOTOS only after migration review.
BEGIN;
CREATE TABLE user_photos (
 kind TEXT NOT NULL CHECK(kind IN ('product','profile','farm')),
 subject_id BIGINT NOT NULL CHECK(subject_id>0),
 owner_id BIGINT NOT NULL REFERENCES users(id),
 data BYTEA NOT NULL CHECK(octet_length(data)>0 AND octet_length(data)<=1000000),
 digest TEXT NOT NULL CHECK(length(digest)=64),
 width BIGINT NOT NULL CHECK(width BETWEEN 1 AND 2048),
 height BIGINT NOT NULL CHECK(height BETWEEN 1 AND 2048),
 PRIMARY KEY(kind,subject_id)
);
COMMIT;

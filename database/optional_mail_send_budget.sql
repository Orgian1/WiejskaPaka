-- Shared application-database send lease and rolling 24-hour attempt budget.
BEGIN;

CREATE TABLE mail_send_budget (
 id BIGINT PRIMARY KEY CHECK(id=1),
 min_interval BIGINT NOT NULL CHECK(min_interval BETWEEN 1 AND 3600),
 daily_limit BIGINT NOT NULL CHECK(daily_limit BETWEEN 1 AND 1000000),
 next_allowed BIGINT NOT NULL,
 owner TEXT,
 lease_until BIGINT NOT NULL,
 paused BIGINT NOT NULL CHECK(paused IN (0,1))
 );
CREATE TABLE mail_send_attempts (
 id TEXT PRIMARY KEY,
 reserved_at BIGINT NOT NULL
);
CREATE INDEX mail_send_attempt_time ON mail_send_attempts(reserved_at);

COMMIT;

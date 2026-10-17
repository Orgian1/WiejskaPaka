-- Local disposable PostgreSQL only; apply before starting the new API.

CREATE TABLE IF NOT EXISTS password_change_access (
    user_id BIGINT PRIMARY KEY REFERENCES users(id),
    attempts BIGINT NOT NULL CHECK(attempts BETWEEN 1 AND 5),
    window_started_at TEXT NOT NULL
);

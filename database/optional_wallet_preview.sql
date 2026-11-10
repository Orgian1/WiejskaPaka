-- Private wallet preview only; never real payment credit.
BEGIN;

CREATE TABLE wallet_preview_accounts (
 user_id BIGINT PRIMARY KEY REFERENCES users(id),
 available_grosze BIGINT NOT NULL DEFAULT 0 CHECK(available_grosze BETWEEN 0 AND 1000000000),
 reserved_grosze BIGINT NOT NULL DEFAULT 0 CHECK(reserved_grosze BETWEEN 0 AND 1000000000),
 revision BIGINT NOT NULL DEFAULT 0 CHECK(revision>=0),
 pin_hash TEXT,
 failures BIGINT NOT NULL DEFAULT 0 CHECK(failures BETWEEN 0 AND 5),
 locked_until BIGINT NOT NULL DEFAULT 0,
 CHECK(available_grosze+reserved_grosze<=1000000000)
);
CREATE TABLE wallet_preview_entries (
 id TEXT PRIMARY KEY,
 user_id BIGINT NOT NULL REFERENCES wallet_preview_accounts(user_id),
 revision BIGINT NOT NULL CHECK(revision>0),
 request_key TEXT NOT NULL,
 payload_hash TEXT NOT NULL,
 kind TEXT NOT NULL CHECK(kind IN ('topup','withdrawal')),
 state TEXT NOT NULL CHECK(state IN ('credited','pending')),
 amount_grosze BIGINT NOT NULL CHECK(amount_grosze BETWEEN 1 AND 100000000),
 available_after BIGINT NOT NULL CHECK(available_after BETWEEN 0 AND 1000000000),
 reserved_after BIGINT NOT NULL CHECK(reserved_after BETWEEN 0 AND 1000000000),
 created_at BIGINT NOT NULL,
 CHECK((kind='topup' AND state='credited') OR (kind='withdrawal' AND state='pending')),
 UNIQUE(user_id,revision),
 UNIQUE(user_id,request_key)
);
COMMIT;

-- Private wallet uncertain-operation fences. No funds move.
BEGIN;

CREATE TABLE wallet_preview_operation_fences (
 user_id BIGINT NOT NULL REFERENCES wallet_preview_accounts(user_id),
 request_key TEXT NOT NULL,
 kind TEXT NOT NULL CHECK(kind IN ('topup','withdrawal')),
 amount_grosze BIGINT NOT NULL CHECK(amount_grosze BETWEEN 1 AND 100000000),
 created_at BIGINT NOT NULL,
 PRIMARY KEY(user_id,request_key)
);

COMMIT;

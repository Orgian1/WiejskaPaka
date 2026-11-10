-- Immutable withdrawal terms and terminal simulation events; no real transfer.
BEGIN;

CREATE TABLE wallet_preview_terms (
 withdrawal_id TEXT PRIMARY KEY REFERENCES wallet_preview_entries(id),
 owner_role TEXT NOT NULL CHECK(owner_role IN ('klient','rolnik')),
 gross_grosze BIGINT NOT NULL CHECK(gross_grosze BETWEEN 1 AND 100000000),
 fee_basis_points BIGINT NOT NULL CHECK(fee_basis_points IN (0,500)),
 fee_grosze BIGINT NOT NULL CHECK(fee_grosze>=0),
 net_grosze BIGINT NOT NULL CHECK(net_grosze>=0),
 CHECK((owner_role='rolnik' AND fee_basis_points=500) OR (owner_role='klient' AND fee_basis_points=0)),
 CHECK(fee_grosze=(gross_grosze*fee_basis_points+5000)/10000),
 CHECK(net_grosze+fee_grosze=gross_grosze)
);
CREATE TABLE wallet_preview_resolutions (
 id TEXT PRIMARY KEY,
 withdrawal_id TEXT NOT NULL UNIQUE REFERENCES wallet_preview_terms(withdrawal_id),
 user_id BIGINT NOT NULL REFERENCES wallet_preview_accounts(user_id),
 actor_id BIGINT NOT NULL REFERENCES users(id),
 revision BIGINT NOT NULL CHECK(revision>0),
 state TEXT NOT NULL CHECK(state IN ('completed_test','cancelled_test')),
 available_after BIGINT NOT NULL CHECK(available_after BETWEEN 0 AND 1000000000),
 reserved_after BIGINT NOT NULL CHECK(reserved_after BETWEEN 0 AND 1000000000),
 created_at BIGINT NOT NULL,
 UNIQUE(user_id,revision)
);
CREATE INDEX wallet_preview_resolutions_user_idx ON wallet_preview_resolutions(user_id);

INSERT INTO wallet_preview_terms
 (withdrawal_id,owner_role,gross_grosze,fee_basis_points,fee_grosze,net_grosze)
 SELECT e.id,u.role,e.amount_grosze,
 CASE WHEN u.role='rolnik' THEN 500 ELSE 0 END,
 CASE WHEN u.role='rolnik' THEN (e.amount_grosze*500+5000)/10000 ELSE 0 END,
 e.amount_grosze-CASE WHEN u.role='rolnik' THEN (e.amount_grosze*500+5000)/10000 ELSE 0 END
 FROM wallet_preview_entries e JOIN users u ON u.id=e.user_id
 WHERE e.kind='withdrawal' AND u.role IN ('klient','rolnik')
 AND NOT EXISTS(SELECT 1 FROM wallet_preview_terms t WHERE t.withdrawal_id=e.id);
COMMIT;

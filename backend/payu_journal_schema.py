"""Durable payment event journal schema for a future verified PayU integration.

These are *preparation* tables, not active wallet or payout endpoints.
Only server-verified payment state may be posted into the wallet ledger.
All amounts are integer grosze; no stored payment credentials.
"""

SQLITE_SCHEMA = """
CREATE TABLE IF NOT EXISTS provider_payment_operations (
    operation_id TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL,
    provider TEXT NOT NULL CHECK(provider IN ('simulated', 'payu')),
    provider_order_id TEXT UNIQUE,
    amount_grosze INTEGER NOT NULL CHECK(amount_grosze > 0),
    currency TEXT NOT NULL DEFAULT 'PLN' CHECK(currency = 'PLN'),
    status TEXT NOT NULL CHECK(status IN
        ('CREATED','PENDING','CONFIRMED','FAILED','CANCELLED','REFUNDED')),
    credited_at INTEGER,
    created_at INTEGER NOT NULL DEFAULT (CAST(strftime('%s','now') AS INTEGER)),
    updated_at INTEGER NOT NULL DEFAULT (CAST(strftime('%s','now') AS INTEGER)),
    CHECK(credited_at IS NULL OR status IN ('CONFIRMED','REFUNDED'))
);
CREATE INDEX IF NOT EXISTS provider_payment_operations_user
    ON provider_payment_operations(user_id, created_at);
CREATE TABLE IF NOT EXISTS provider_payment_events (
    event_id TEXT PRIMARY KEY,
    operation_id TEXT NOT NULL REFERENCES provider_payment_operations(operation_id),
    event_type TEXT NOT NULL,
    verified INTEGER NOT NULL DEFAULT 0 CHECK(verified IN (0,1)),
    received_at INTEGER NOT NULL DEFAULT (CAST(strftime('%s','now') AS INTEGER))
);
CREATE INDEX IF NOT EXISTS provider_payment_events_operation
    ON provider_payment_events(operation_id);
CREATE TABLE IF NOT EXISTS provider_refund_requests (
    refund_id TEXT PRIMARY KEY,
    operation_id TEXT NOT NULL REFERENCES provider_payment_operations(operation_id),
    amount_grosze INTEGER NOT NULL CHECK(amount_grosze > 0),
    status TEXT NOT NULL CHECK(status IN ('REQUESTED','PENDING','COMPLETED','FAILED')),
    created_at INTEGER NOT NULL DEFAULT (CAST(strftime('%s','now') AS INTEGER))
);
CREATE TABLE IF NOT EXISTS provider_payout_requests (
    payout_id TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('klient','rolnik')),
    gross_grosze INTEGER NOT NULL CHECK(gross_grosze > 0),
    net_grosze INTEGER NOT NULL CHECK(net_grosze >= 0),
    fee_grosze INTEGER NOT NULL CHECK(fee_grosze >= 0),
    status TEXT NOT NULL CHECK(status IN
        ('REQUESTED','APPROVED','SENT','SETTLED','REJECTED','FAILED')),
    created_at INTEGER NOT NULL DEFAULT (CAST(strftime('%s','now') AS INTEGER)),
    CHECK(gross_grosze = net_grosze + fee_grosze)
);
"""


def initialize_test_journal(connection):
    """Only use in isolated test databases, not as a production migration."""
    connection.execute('PRAGMA foreign_keys=ON')
    connection.executescript(SQLITE_SCHEMA)

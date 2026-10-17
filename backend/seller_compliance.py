# Testowy proces zgodności sprzedawcy; bez danych identyfikacyjnych.
from datetime import datetime, timezone

RULES_VERSION = '2026-10-draft'

def create_compliance_tables(con):
    con.execute('''CREATE TABLE IF NOT EXISTS seller_compliance (
        farmer_id INTEGER PRIMARY KEY REFERENCES users(id),
        rules_version TEXT NOT NULL,
        acknowledged_at TEXT NOT NULL,
        review_status TEXT NOT NULL DEFAULT 'pending' CHECK(review_status IN ('pending','approved','needs_information','rejected')),
        reviewed_by INTEGER REFERENCES users(id),
        reviewed_at TEXT,
        review_reason TEXT
    )''')
    con.execute('''CREATE TABLE IF NOT EXISTS seller_compliance_events (
        id INTEGER PRIMARY KEY,
        farmer_id INTEGER NOT NULL REFERENCES users(id),
        actor_id INTEGER NOT NULL REFERENCES users(id),
        event_type TEXT NOT NULL,
        created_at TEXT NOT NULL
    )''')

def seller_compliance_status(con, farmer_id):
    row = con.execute('SELECT rules_version, acknowledged_at, review_status, reviewed_at FROM seller_compliance WHERE farmer_id=?', (farmer_id,)).fetchone()
    # Nie zakładamy prawnych progów DAC7 na podstawie liczby transakcji.
    count = con.execute("SELECT COUNT(*) AS n FROM orders WHERE farmer_id=? AND status NOT IN ('anulowane_testowo')", (farmer_id,)).fetchone()['n']
    return {'rules_acknowledged': bool(row), 'rules_version': row['rules_version'] if row else None,
            'review_status': row['review_status'] if row else 'not_started',
            'order_count_observed': count,
            'identity_data_collection': 'disabled_until_secure_provider',
            'can_receive_real_payouts': False,
            'notice': 'Weryfikacja i wymogi DAC7/KYC wymagają ustalenia z operatorem płatności i doradcą prawnym.'}

def acknowledge_seller_rules(con, farmer_id, version):
    if version != RULES_VERSION:
        raise ValueError('Nieobsługiwana wersja zasad')
    now = datetime.now(timezone.utc).isoformat()
    previous = con.execute('SELECT rules_version FROM seller_compliance WHERE farmer_id=?', (farmer_id,)).fetchone()
    if previous and previous['rules_version'] == version:
        return
    con.execute('''INSERT INTO seller_compliance(farmer_id,rules_version,acknowledged_at,review_status)
        VALUES(?,?,?,'pending') ON CONFLICT(farmer_id) DO UPDATE SET
        rules_version=excluded.rules_version,acknowledged_at=excluded.acknowledged_at,
        review_status='pending',reviewed_by=NULL,reviewed_at=NULL,review_reason=NULL''', (farmer_id,version,now))
    con.execute('INSERT INTO seller_compliance_events(farmer_id,actor_id,event_type,created_at) VALUES(?,?,?,?)',
                (farmer_id,farmer_id,'rules_acknowledged',now))

def review_seller_account(con, farmer_id, admin_id, decision, reason):
    now = datetime.now(timezone.utc).isoformat()
    updated = con.execute('''UPDATE seller_compliance SET review_status=?, reviewed_by=?, reviewed_at=?, review_reason=?
        WHERE farmer_id=?''', (decision,admin_id,now,reason,farmer_id))
    if updated.rowcount != 1:
        raise ValueError('Sprzedawca nie potwierdził jeszcze zasad')
    con.execute('INSERT INTO seller_compliance_events(farmer_id,actor_id,event_type,created_at) VALUES(?,?,?,?)',
                (farmer_id,admin_id,'review_'+decision,now))

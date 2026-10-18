# Testowy proces zgodności sprzedawcy; bez danych identyfikacyjnych.
from datetime import datetime, timezone

RULES_VERSION = '2026-10-draft'
PROFILE_REMINDER_THRESHOLD = 20

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
    # A completed multi-product shipment is one transaction. Every linked row
    # must be received and belong to the shipment's buyer and seller.
    grouped = con.execute("""SELECT COUNT(*) AS n FROM shipment_groups s
        WHERE s.farmer_id=?
        AND EXISTS (SELECT 1 FROM shipment_order_links l WHERE l.shipment_id=s.id)
        AND NOT EXISTS (SELECT 1 FROM shipment_order_links l
            JOIN orders o ON o.id=l.order_id WHERE l.shipment_id=s.id
            AND (o.status<>'odebrane' OR o.farmer_id<>s.farmer_id OR o.buyer_id<>s.buyer_id))""",
        (farmer_id,)).fetchone()['n']
    standalone = con.execute("""SELECT COUNT(*) AS n FROM orders o
        WHERE o.farmer_id=? AND o.status='odebrane'
        AND NOT EXISTS (SELECT 1 FROM shipment_order_links l WHERE l.order_id=o.id)""",
        (farmer_id,)).fetchone()['n']
    completed = grouped + standalone
    return {'rules_acknowledged': bool(row), 'rules_version': row['rules_version'] if row else None,
            'review_status': row['review_status'] if row else 'not_started',
            'order_count_observed': count,
            'current_rules_version': RULES_VERSION,
            'completed_transaction_count': completed,
            'profile_reminder_threshold': PROFILE_REMINDER_THRESHOLD,
            'profile_reminder_due': completed >= PROFILE_REMINDER_THRESHOLD and
                (not row or row['review_status'] != 'approved' or row['rules_version'] != RULES_VERSION),
            'threshold_basis': 'product_rule_not_legal_threshold',
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

def review_seller_account(con, farmer_id, admin_id, decision, reason, *, expected=None):
    now = datetime.now(timezone.utc).isoformat()
    condition = ''
    parameters = [decision, admin_id, now, reason, farmer_id]
    if expected is not None:
        condition = ''' AND rules_version=? AND review_status=?
            AND (reviewed_at=? OR (reviewed_at IS NULL AND ?=1))'''
        parameters.extend([expected['rules_version'], expected['review_status'],
                           expected['reviewed_at'], int(expected['reviewed_at'] is None)])
    updated = con.execute('''UPDATE seller_compliance SET review_status=?, reviewed_by=?, reviewed_at=?, review_reason=?
        WHERE farmer_id=?''' + condition, tuple(parameters))
    if updated.rowcount != 1:
        raise ValueError('Profil zmienił się lub nie potwierdzono zasad. Odśwież kolejkę.')
    con.execute('INSERT INTO seller_compliance_events(farmer_id,actor_id,event_type,created_at) VALUES(?,?,?,?)',
                (farmer_id,admin_id,'review_'+decision,now))


def seller_review_queue(con, status=None, limit=20, offset=0):
    """Bounded queue without contact data, identity data or review reasons."""
    allowed = {'pending', 'approved', 'needs_information', 'rejected'}
    if type(limit) is not int or not 1 <= limit <= 50 or type(offset) is not int or not 0 <= offset <= 10000:
        raise ValueError('Nieprawidłowa paginacja')
    if status is not None and status not in allowed:
        raise ValueError('Nieprawidłowy filtr')
    where = " WHERE u.role='rolnik'"
    parameters = ()
    if status is not None:
        where += ' AND c.review_status=?'
        parameters = (status,)
    source = ' FROM seller_compliance c JOIN users u ON u.id=c.farmer_id'
    total = con.execute('SELECT COUNT(*) AS n'+source+where, parameters).fetchone()['n']
    rows = con.execute('''SELECT c.farmer_id,c.rules_version,c.acknowledged_at,
        c.review_status,c.reviewed_at''' + source + where + ' ORDER BY c.farmer_id LIMIT ? OFFSET ?',
        parameters + (limit, offset)).fetchall()
    return {'mode': 'test', 'profiles': [dict(row) for row in rows], 'total': total,
            'limit': limit, 'offset': offset, 'has_more': offset+len(rows)<total}

"""Private suppression registry; NOT an SNS/HTTP ingestion endpoint.

Only an independently authenticated administrative/provider path may call block.
Raw notifications and client-provided verification booleans are never accepted.
"""
import hashlib
from backend.order_mail_outbox import _require_transaction
from backend.smtp_reset_transport import address

SCHEMA_SQLITE='''
CREATE TABLE IF NOT EXISTS mail_recipient_blocks (
 recipient_hash TEXT PRIMARY KEY,
 reason TEXT NOT NULL CHECK(reason IN ('permanent_bounce','complaint')),
 created_at INTEGER NOT NULL
);
'''


def digest(email):return hashlib.sha256(address(email).lower().encode()).hexdigest()


def block(con,email,reason,*,now):
    _require_transaction(con)
    if reason not in ('permanent_bounce','complaint') or type(now) is not int or now<0:
        raise ValueError('MAIL_SUPPRESSION_REJECTED')
    con.execute('''INSERT INTO mail_recipient_blocks VALUES(?,?,?)
        ON CONFLICT(recipient_hash) DO UPDATE SET
        reason=CASE WHEN excluded.reason='complaint' THEN 'complaint' ELSE mail_recipient_blocks.reason END,
        created_at=CASE WHEN excluded.created_at<mail_recipient_blocks.created_at
                       THEN excluded.created_at ELSE mail_recipient_blocks.created_at END''',
        (digest(email),reason,now))


def blocked(con,email):
    return con.execute('SELECT 1 FROM mail_recipient_blocks WHERE recipient_hash=?',(digest(email),)).fetchone() is not None

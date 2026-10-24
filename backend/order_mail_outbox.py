"""Explicit purchase-mail ledger. Not attached to HTTP or an automatic worker.

No address or PIN is stored here. A trusted caller supplies a verification
lookup, vault and transport. Started attempts are never automatically resent.
"""
from datetime import datetime, timezone
import hashlib
import re
import secrets

from backend.order_mail import checkout_purchase
from backend.reset_mail_queue import transaction
from backend.smtp_reset_transport import address

SCHEMA_SQLITE='''
CREATE TABLE IF NOT EXISTS order_mail_outbox (
 id TEXT PRIMARY KEY,
 buyer_id INTEGER NOT NULL REFERENCES users(id),
 request_key TEXT NOT NULL,
 recipient_hash TEXT NOT NULL,
 state TEXT NOT NULL CHECK(state IN ('queued','started','accepted','uncertain','failed','skipped')),
 created_at INTEGER NOT NULL,
 started_at INTEGER,
 result TEXT,
 UNIQUE(buyer_id,request_key),
 FOREIGN KEY(buyer_id,request_key) REFERENCES checkout_idempotency(buyer_id,request_key)
);
CREATE INDEX IF NOT EXISTS order_mail_ready ON order_mail_outbox(state,created_at,id);
'''


def quarantine_restored(con):
    """Offline restored copy only: do not replay historical queued purchases."""
    _require_transaction(con)
    con.execute("UPDATE order_mail_outbox SET state='skipped',result='RESTORED_COPY' WHERE state='queued'")
    con.execute("UPDATE order_mail_outbox SET state='uncertain',result='DELIVERY_UNCERTAIN' WHERE state='started'")


def _postgres(con):
    from backend.pg_adapter import PgConnection
    return isinstance(con,PgConnection)


def _require_transaction(con):
    if _postgres(con):
        from psycopg.pq import TransactionStatus
        if con.connection.info.transaction_status==TransactionStatus.INTRANS:return
    elif con.in_transaction:return
    raise ValueError('ORDER_MAIL_TRANSACTION_REQUIRED')


def _time(now):
    if type(now) is not int or now<0:raise ValueError('ORDER_MAIL_TIME_REJECTED')
    return now


def recipient_hash(email):
    return hashlib.sha256(address(email).encode()).hexdigest()


def enqueue(con,buyer_id,request_key,*,now):
    """Call in the same transaction as a persisted checkout, once per purchase."""
    _require_transaction(con);now=_time(now)
    if (type(buyer_id) is not int or buyer_id<1 or not isinstance(request_key,str)
            or not re.fullmatch(r'(?:direct:)?[A-Za-z0-9_-]{12,100}',request_key)):
        raise ValueError('ORDER_MAIL_PURCHASE_REJECTED')
    row=con.execute('''SELECT u.email FROM checkout_idempotency c JOIN users u ON u.id=c.buyer_id
        WHERE c.buyer_id=? AND c.request_key=? AND u.role='klient' ''',(buyer_id,request_key)).fetchone()
    if row is None:raise ValueError('ORDER_MAIL_PURCHASE_UNAVAILABLE')
    job_id=secrets.token_hex(16)
    con.execute('''INSERT INTO order_mail_outbox(id,buyer_id,request_key,recipient_hash,state,created_at)
        VALUES(?,?,?,?,'queued',?) ON CONFLICT(buyer_id,request_key) DO NOTHING''',
        (job_id,buyer_id,request_key,recipient_hash(row['email']),now))
    return con.execute('SELECT id FROM order_mail_outbox WHERE buyer_id=? AND request_key=?',
                       (buyer_id,request_key)).fetchone()['id']


def dispatch_once(connect,vault,transport,verified_recipient,*,clock):
    """Exactly one submission attempt, after durable start and private authorization.

    verified_recipient(con,buyer_id,email) must query confirmed account ownership;
    neither a request parameter nor SES domain verification constitutes that proof.
    A crash or timeout after start becomes uncertain. No automatic retries occur.
    """
    con=connect();job=None
    try:
        with transaction(con):
            now=_time(clock())
            con.execute("""UPDATE order_mail_outbox SET state='uncertain',result='DELIVERY_UNCERTAIN'
                WHERE state='started' AND started_at<=?""",(now-120,))
            lock=' FOR UPDATE SKIP LOCKED' if _postgres(con) else ''
            job=con.execute("SELECT * FROM order_mail_outbox WHERE state='queued' ORDER BY created_at,id LIMIT 1"+lock).fetchone()
            if job is None:return 'IDLE'
            user=con.execute("SELECT email FROM users WHERE id=? AND role='klient'",(job['buyer_id'],)).fetchone()
            try:
                eligible=(user is not None and recipient_hash(user['email'])==job['recipient_hash']
                          and verified_recipient(con,job['buyer_id'],user['email']) is True)
                if not eligible:raise ValueError('Ineligible recipient')
                purchase=checkout_purchase(con,vault,job['buyer_id'],job['request_key'],
                                           now=datetime.fromtimestamp(now,timezone.utc))
            except Exception:
                con.execute("UPDATE order_mail_outbox SET state='skipped',result='INELIGIBLE' WHERE id=?",(job['id'],))
                return 'SKIPPED'
            updated=con.execute("UPDATE order_mail_outbox SET state='started',started_at=? WHERE id=? AND state='queued'",
                                (now,job['id']))
            if updated.rowcount!=1:return 'STALE'
        # The transaction above has committed before any external SMTP call.
        try:
            response=transport(user['email'],purchase,email_verified=True)
            expected={'status','accepted_by_server','delivery_confirmed','retryable'}
            if (not isinstance(response,dict) or set(response)!=expected
                    or response['delivery_confirmed'] is not False
                    or type(response['accepted_by_server']) is not bool
                    or type(response['retryable']) is not bool):raise ValueError('Invalid transport result')
            status=response['status']
            if status=='ACCEPTED' and response['accepted_by_server'] is True:state='accepted'
            elif status in ('DELIVERY_UNCERTAIN','ACCEPTED') or response['accepted_by_server']:state='uncertain';status='DELIVERY_UNCERTAIN'
            elif status in ('REJECTED','CONNECTION_FAILED','TLS_FAILED','MESSAGE_REJECTED','DISABLED'):state='failed'
            else:raise ValueError('Invalid transport status')
        except Exception:state='uncertain';status='DELIVERY_UNCERTAIN'
        with transaction(con):
            updated=con.execute("UPDATE order_mail_outbox SET state=?,result=? WHERE id=? AND state='started'",
                                (state,status,job['id']))
        return status if updated.rowcount==1 else 'STALE'
    finally:
        if _postgres(con):con.connection.close()
        else:con.close()

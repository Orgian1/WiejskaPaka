"""Atomic checkout capture for proven recipients. Never opens SMTP."""
from datetime import datetime, timezone
from backend import email_ownership as proof, order_mail_outbox as outbox


def configure(con,environ,*,postgres):
    if environ.get('WP_ENABLE_ORDER_MAIL_QUEUE')!='1':return False
    if environ.get('WP_ENABLE_EMAIL_VERIFICATION')!='1':
        raise ValueError('ORDER_MAIL_REQUIRES_ACCOUNT_VERIFICATION')
    if not postgres:con.executescript(outbox.SCHEMA_SQLITE)
    con.execute('SELECT id,buyer_id,request_key FROM order_mail_outbox LIMIT 0')
    con.execute('SELECT user_id,email_hash,verified_at FROM account_email_proofs LIMIT 0')
    return True


def capture(con,buyer_id,request_key):
    """Caller owns checkout transaction. Unverified purchases are not backfilled."""
    outbox._require_transaction(con)
    row=con.execute('SELECT email FROM users WHERE id=?',(buyer_id,)).fetchone()
    if not row or not proof.verified_recipient(con,buyer_id,row['email']):return None
    return outbox.enqueue(con,buyer_id,request_key,now=int(datetime.now(timezone.utc).timestamp()))

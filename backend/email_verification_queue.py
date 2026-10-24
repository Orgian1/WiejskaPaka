"""Bounded encrypted verification outbox, explicit delivery only; no background thread."""
import hashlib
import secrets
from contextlib import contextmanager
from backend import email_ownership as proof
from backend.order_mail_outbox import _postgres, _require_transaction
from backend.reset_mail_queue import transaction

SCHEMA_SQLITE = proof.SCHEMA_SQLITE + '''
CREATE TABLE IF NOT EXISTS email_verification_limits (
 bucket TEXT PRIMARY KEY, attempts INTEGER NOT NULL, window_started INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS email_verification_queue (
 id TEXT PRIMARY KEY,
 user_id INTEGER NOT NULL UNIQUE REFERENCES users(id),
 event TEXT NOT NULL CHECK(event='email_verification'),
 token_hash TEXT NOT NULL,
 key_id TEXT NOT NULL,
 payload BLOB,
 created_at INTEGER NOT NULL,
 expires_at INTEGER NOT NULL,
 state TEXT NOT NULL CHECK(state IN ('queued','started','accepted','uncertain','failed','expired')),
 started_at INTEGER
);
'''


def budget(con, user_id, peer, action, *, now):
    """Commit denials as well as successes. Never trust forwarded headers here."""
    _require_transaction(con);proof._time(now)
    if action not in ('issue','consume') or not isinstance(peer,str) or len(peer)>128:
        raise ValueError('EMAIL_VERIFICATION_BUDGET_REJECTED')
    if _postgres(con):
        con.execute('SELECT pg_advisory_xact_lock(hashtextextended(?,0))',('wp:email-verification:budget',))
    con.execute('DELETE FROM email_verification_limits WHERE window_started<=?',(now-3600,))
    caps=(('global',1000),('ip:'+hashlib.sha256(peer.encode()).hexdigest(),30 if action=='issue' else 100),
          ('account:'+str(user_id),5 if action=='issue' else 30))
    allowed=True
    for scope,limit in caps:
        key=action+':'+scope
        row=con.execute('SELECT * FROM email_verification_limits WHERE bucket=?',(key,)).fetchone()
        if row and (row['window_started']>now or row['attempts']>=limit):
            return False
        con.execute('''INSERT INTO email_verification_limits VALUES(?,?,?)
            ON CONFLICT(bucket) DO UPDATE SET attempts=excluded.attempts''',
            (key,(row['attempts'] if row else 0)+1,row['window_started'] if row else now))
    return allowed


def enqueue(con, keys, user_id, *, now):
    _require_transaction(con)
    token=proof.issue(con,user_id,now=now)
    if token is None:return False
    user=con.execute('SELECT email FROM users WHERE id=?',(user_id,)).fetchone()
    job={'id':secrets.token_hex(16),'user_id':user_id,'event':'email_verification',
         'token_hash':hashlib.sha256(token.encode()).hexdigest(),'key_id':keys.active,
         'created_at':now,'expires_at':now+proof.TTL}
    payload=keys.encrypt(job,user['email'],token)
    # One slot per account bounds storage and replaces any obsolete encrypted token.
    con.execute('DELETE FROM email_verification_queue WHERE user_id=?',(user_id,))
    con.execute('''INSERT INTO email_verification_queue
        (id,user_id,event,token_hash,key_id,payload,created_at,expires_at,state)
        VALUES(?,?,?,?,?,?,?,?,'queued')''',
        (*[job[k] for k in ('id','user_id','event','token_hash','key_id')],payload,now,now+proof.TTL))
    return True


def quarantine_restored(con):
    _require_transaction(con)
    con.execute('DELETE FROM account_email_proofs')
    con.execute("UPDATE email_verification_queue SET payload=NULL,state='expired' WHERE state='queued'")
    con.execute("UPDATE email_verification_queue SET payload=NULL,state='uncertain' WHERE state='started'")


@contextmanager
def _connection(connect):
    con=connect()
    try:yield con
    finally:
        if _postgres(con):con.connection.close()
        else:con.close()


def dispatch_once(connect, keys, transport, *, now):
    """At most one SMTP attempt; transport takes recipient/token, no retries on uncertainty."""
    proof._time(now)
    with _connection(connect) as con:
        with transaction(con):
            con.execute("UPDATE email_verification_queue SET payload=NULL,state='uncertain' WHERE state='started' AND started_at<=?",(now-120,))
            suffix=' FOR UPDATE SKIP LOCKED' if _postgres(con) else ''
            row=con.execute("SELECT * FROM email_verification_queue WHERE state='queued' ORDER BY created_at,id LIMIT 1"+suffix).fetchone()
            if not row:return 'IDLE'
            job_id=row['id']
            valid=False
            try:
                delivery=keys.decrypt(row)
                owner=con.execute('SELECT email FROM users WHERE id=?',(row['user_id'],)).fetchone()
                active=con.execute('SELECT * FROM account_email_proofs WHERE user_id=?',(row['user_id'],)).fetchone()
                valid=bool(owner and active and row['created_at']<=now<row['expires_at'] and
                    active['token_hash']==row['token_hash'] and active['verified_at'] is None and
                    active['email_hash']==proof.recipient_hash(owner['email']) and
                    proof.recipient_hash(delivery.recipient)==active['email_hash'])
            except Exception:pass
            if not valid:
                con.execute("UPDATE email_verification_queue SET payload=NULL,state='expired' WHERE id=?",(job_id,))
                return 'SKIPPED'
            con.execute("UPDATE email_verification_queue SET payload=NULL,state='started',started_at=? WHERE id=?",(now,job_id))
        # Ciphertext erased and started marker committed BEFORE network I/O.
        try:
            result=transport(delivery.recipient,delivery.token)
            expected={'status','accepted_by_server','delivery_confirmed','retryable'}
            if (not isinstance(result,dict) or set(result)!=expected or
                    result['delivery_confirmed'] is not False or
                    type(result['accepted_by_server']) is not bool or type(result['retryable']) is not bool):
                raise ValueError('EMAIL_VERIFICATION_TRANSPORT_REJECTED')
            status=result['status']
            if status=='ACCEPTED' and result['accepted_by_server'] is True:state='accepted'
            elif status=='ACCEPTED' or result['accepted_by_server']:state='uncertain'
            elif status in ('DISABLED','MESSAGE_REJECTED','REJECTED','CONNECTION_FAILED','TLS_FAILED'):state='failed'
            else:state='uncertain'
        except Exception:state='uncertain'
        with transaction(con):
            con.execute("UPDATE email_verification_queue SET state=? WHERE id=? AND state='started'",(state,job_id))
        return state.upper()

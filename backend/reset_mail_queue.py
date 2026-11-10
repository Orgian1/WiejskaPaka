"""Disconnected SQLite/PostgreSQL reset outbox. No HTTP, environment, worker or network hooks.

Every mutating call requires the caller's transaction; use transaction() to
serialize writers. Commit start() before any external submission. An expired
started lease is uncertain, never eligible for automatic resubmission.
"""
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
import os
import re
import secrets
import sqlite3

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from backend import password_reset as reset
from backend.smtp_reset_transport import address

SCHEMA = '''
CREATE TABLE IF NOT EXISTS reset_mail_queue (
 id TEXT PRIMARY KEY,
 user_id INTEGER NOT NULL REFERENCES users(id),
 token_hash TEXT NOT NULL UNIQUE,
 event TEXT NOT NULL CHECK(event='password_reset'),
 key_id TEXT NOT NULL,
 payload BLOB,
 created_at INTEGER NOT NULL,
 expires_at INTEGER NOT NULL,
 state TEXT NOT NULL CHECK(state IN ('queued','leased','accepted','uncertain','failed','expired')),
 attempts INTEGER NOT NULL DEFAULT 0 CHECK(attempts BETWEEN 0 AND 3),
 available_at INTEGER NOT NULL,
 owner TEXT,
 lease_until INTEGER,
 started_at INTEGER,
 result TEXT,
 CHECK(expires_at>created_at),
 CHECK((state IN ('queued','leased') AND payload IS NOT NULL) OR
       (state IN ('accepted','uncertain','failed','expired') AND payload IS NULL)),
 CHECK((state='leased' AND owner IS NOT NULL AND lease_until IS NOT NULL) OR
       (state!='leased' AND owner IS NULL AND lease_until IS NULL AND started_at IS NULL))
);
CREATE INDEX IF NOT EXISTS reset_mail_ready ON reset_mail_queue(state,available_at,created_at);
'''


@dataclass(frozen=True)
class Lease:
    job_id: str
    owner: str = field(repr=False)


@dataclass(frozen=True)
class Delivery:
    recipient: str = field(repr=False)
    token: str = field(repr=False)


class KeyRing:
    """Explicit keys supplied privately by a future caller, never generated on restart."""
    def __init__(self, keys, active):
        if not isinstance(keys, dict) or active not in keys or not keys:
            raise ValueError('QUEUE_KEY_CONFIGURATION_REJECTED')
        if any(not isinstance(k,str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,40}',k)
               or not isinstance(v,bytes) or len(v)!=32 for k,v in keys.items()):
            raise ValueError('QUEUE_KEY_CONFIGURATION_REJECTED')
        self._keys=dict(keys)
        self.active=active

    def encrypt(self, row, recipient, token):
        nonce=os.urandom(12)
        body=json.dumps({'recipient':recipient,'token':token},separators=(',',':')).encode()
        return nonce+AESGCM(self._keys[row['key_id']]).encrypt(nonce,body,_aad(row))

    def decrypt(self, row):
        try:
            payload=bytes(row['payload'])
            body=AESGCM(self._keys[row['key_id']]).decrypt(payload[:12],payload[12:],_aad(row))
            obj=json.loads(body)
            recipient=address(obj['recipient']);token=obj['token']
            if not re.fullmatch(r'[A-Za-z0-9_-]{43}',token) or reset.digest(token)!=row['token_hash']:
                raise ValueError('invalid token')
            return Delivery(recipient,token)
        except Exception:
            raise ValueError('QUEUE_PAYLOAD_REJECTED') from None


def _aad(row):
    return json.dumps([row[k] for k in ('id','user_id','event','token_hash','key_id','created_at','expires_at')],
                      separators=(',',':')).encode()


def _postgres(con):
    from backend.pg_adapter import PgConnection
    return isinstance(con,PgConnection)


def _require(con):
    if _postgres(con):
        from psycopg.pq import TransactionStatus
        from psycopg.rows import dict_row
        if con.connection.row_factory is dict_row and con.connection.info.transaction_status==TransactionStatus.INTRANS:
            return
    elif isinstance(con,sqlite3.Connection) and con.row_factory is sqlite3.Row and con.in_transaction:
        return
    raise ValueError('QUEUE_REQUIRES_TRANSACTION')


def _time(now):
    if type(now) is not int or now<0:
        raise ValueError('QUEUE_INVALID_TIME')
    return now


@contextmanager
def transaction(con):
    if _postgres(con):
        from psycopg.pq import TransactionStatus
        from psycopg.rows import dict_row
        raw=con.connection
        if raw.row_factory is not dict_row or raw.info.transaction_status!=TransactionStatus.IDLE:
            raise ValueError('QUEUE_REQUIRES_OWN_TRANSACTION')
        with raw.transaction():
            yield con
        return
    if not isinstance(con,sqlite3.Connection) or con.in_transaction:
        raise ValueError('QUEUE_REQUIRES_OWN_TRANSACTION')
    con.execute('BEGIN IMMEDIATE')
    try:
        yield con
        con.commit()
    except BaseException:
        con.rollback()
        raise


def issue(con, keys, email, *, now):
    """Issue token and encrypted job atomically; unknown accounts never get a job.

    The caller must return the same public response regardless of this internal
    result. The separate opt-in test HTTP route calls this method; the legacy
    local-mailbox demo API remains independent.
    """
    _require(con);now=_time(now)
    token=reset.issue(con,email,now=datetime.fromtimestamp(now,timezone.utc))
    if token is None:return None
    row=con.execute('''SELECT r.*,u.email FROM password_reset_tokens r
        JOIN users u ON u.id=r.user_id WHERE r.token_hash=?''',(reset.digest(token),)).fetchone()
    if row is None:return None
    recipient=address(row['email'])
    job={'id':secrets.token_hex(16),'user_id':row['user_id'],'token_hash':row['token_hash'],
         'event':'password_reset','key_id':keys.active,'created_at':now,'expires_at':now+900}
    payload=keys.encrypt(job,recipient,token)
    con.execute('''INSERT INTO reset_mail_queue
        (id,user_id,token_hash,event,key_id,payload,created_at,expires_at,state,available_at)
        VALUES(?,?,?,?,?,?,?,?,'queued',?)''',
        (*[job[k] for k in ('id','user_id','token_hash','event','key_id')],payload,now,now+900,now))
    return job['id']


def _terminal(con, row, state, result):
    con.execute('''UPDATE reset_mail_queue SET state=?,result=?,payload=NULL,owner=NULL,
        lease_until=NULL,started_at=NULL WHERE id=?''',(state,result,row['id']))


def recover(con, *, now):
    """Recover only unstarted leases. A started orphan can have reached SMTP."""
    _require(con);now=_time(now)
    if _postgres(con):
        rows=con.execute("""SELECT * FROM reset_mail_queue
            WHERE (state='leased' AND lease_until<=?) OR (state='queued' AND expires_at<=?)
            ORDER BY id FOR UPDATE SKIP LOCKED""",(now,now)).fetchall()
    else:
        rows=con.execute("SELECT * FROM reset_mail_queue WHERE state='leased' AND lease_until<=?",(now,)).fetchall()
    for row in rows:
        if row['state']=='queued':_terminal(con,row,'expired','EXPIRED')
        elif row['started_at'] is not None:_terminal(con,row,'uncertain','LEASE_LOST_AFTER_START')
        elif row['expires_at']<=now:_terminal(con,row,'expired','EXPIRED')
        else:
            con.execute("UPDATE reset_mail_queue SET state='queued',owner=NULL,lease_until=NULL WHERE id=?",(row['id'],))
    if not _postgres(con):
        con.execute("""UPDATE reset_mail_queue SET state='expired',result='EXPIRED',payload=NULL
            WHERE state='queued' AND expires_at<=?""",(now,))


def claim(con, *, now, lease_seconds=120):
    _require(con);now=_time(now)
    if type(lease_seconds) is not int or not 30<=lease_seconds<=300:raise ValueError('QUEUE_INVALID_LEASE')
    recover(con,now=now)
    lock=' FOR UPDATE SKIP LOCKED' if _postgres(con) else ''
    row=con.execute("""SELECT * FROM reset_mail_queue WHERE state='queued' AND available_at<=?
        AND created_at<=? AND expires_at>? ORDER BY created_at,id LIMIT 1"""+lock,(now,now,now)).fetchone()
    if row is None:return None
    owner=secrets.token_hex(32)
    con.execute("UPDATE reset_mail_queue SET state='leased',owner=?,lease_until=? WHERE id=?",
                (owner,now+lease_seconds,row['id']))
    return Lease(row['id'],owner)


def _owned(con, lease, now):
    lock=' FOR UPDATE' if _postgres(con) else ''
    return con.execute("""SELECT * FROM reset_mail_queue WHERE id=? AND owner=?
        AND state='leased' AND lease_until>?"""+lock,(lease.job_id,lease.owner,now)).fetchone()


def start(con, keys, lease, *, now):
    """Validate and persist the point after which a crash is ambiguous.

    Returned secrets may be used only AFTER this transaction has committed.
    The external operation must finish within the remaining lease duration.
    """
    _require(con);now=_time(now)
    row=_owned(con,lease,now)
    if row is None or row['started_at'] is not None:return None
    token=con.execute('''SELECT r.*,u.password_hash,u.email FROM password_reset_tokens r
        JOIN users u ON u.id=r.user_id WHERE r.token_hash=?''',(row['token_hash'],)).fetchone()
    if (row['created_at']>now or row['expires_at']<=now or token is None
            or reset.utc_datetime(token['expires_at']).timestamp()<=now
            or reset.utc_datetime(token['created_at']).timestamp()>now
            or token['user_id']!=row['user_id']
            or not secrets.compare_digest(token['password_version'],reset.digest(token['password_hash']))):
        _terminal(con,row,'expired','INVALIDATED');return None
    if row['attempts']>=3:
        _terminal(con,row,'failed','ATTEMPTS_EXHAUSTED');return None
    try:
        delivery=keys.decrypt(row)
        if delivery.recipient!=token['email']:raise ValueError('recipient changed')
    except ValueError:
        _terminal(con,row,'failed','PAYLOAD_REJECTED');return None
    con.execute('UPDATE reset_mail_queue SET started_at=?,attempts=attempts+1 WHERE id=?',(now,row['id']))
    return delivery


def finish(con, lease, outcome, *, now):
    """Persist a sanitized adapter outcome. Reject stale workers and invalid combinations."""
    _require(con);now=_time(now)
    status=outcome.get('status') if isinstance(outcome,dict) else None
    allowed={'ACCEPTED','DELIVERY_UNCERTAIN','REJECTED','CONNECTION_FAILED','TLS_FAILED','MESSAGE_REJECTED','DISABLED'}
    if (not isinstance(status,str) or status not in allowed or type(outcome.get('retryable')) is not bool
            or type(outcome.get('accepted_by_server')) is not bool
            or outcome.get('delivery_confirmed') is not False
            or outcome['accepted_by_server']!=(status=='ACCEPTED')
            or (outcome['retryable'] and status not in {'REJECTED','CONNECTION_FAILED'})):
        raise ValueError('QUEUE_INVALID_OUTCOME')
    row=_owned(con,lease,now)
    if row is None or row['started_at'] is None or row['started_at']>now:return False
    if status=='ACCEPTED':_terminal(con,row,'accepted',status)
    elif status=='DELIVERY_UNCERTAIN':_terminal(con,row,'uncertain',status)
    elif outcome['retryable'] and row['attempts']<3 and now+30*(2**(row['attempts']-1))<row['expires_at']:
        con.execute("""UPDATE reset_mail_queue SET state='queued',result=?,available_at=?,
            owner=NULL,lease_until=NULL,started_at=NULL WHERE id=?""",
            (status,now+30*(2**(row['attempts']-1)),row['id']))
    else:_terminal(con,row,'failed',status)
    return True


def dispatch_once(connect, keys, transport, *, clock, lease_seconds=120):
    """One explicit task; caller supplies connection, clock AND transport.

    There is no default network transport or background loop. Secrets cross
    only the injected transport boundary after start has durably committed.
    Crashes/commit failures leave the marker for conservative recovery.
    """
    con=connect()
    try:
        with transaction(con):
            lease=claim(con,now=clock(),lease_seconds=lease_seconds)
        if lease is None:return 'IDLE'
        with transaction(con):
            delivery=start(con,keys,lease,now=clock())
        if delivery is None:return 'SKIPPED'
        try:
            result=transport(delivery.recipient,delivery.token)
        except Exception:
            # The callback can have reached DATA before failing. Never guess.
            result={'status':'DELIVERY_UNCERTAIN','accepted_by_server':False,
                    'delivery_confirmed':False,'retryable':False}
        with transaction(con):
            try:
                recorded=finish(con,lease,result,now=clock())
            except ValueError:
                result={'status':'DELIVERY_UNCERTAIN','accepted_by_server':False,
                        'delivery_confirmed':False,'retryable':False}
                recorded=finish(con,lease,result,now=clock())
        return result['status'] if recorded else 'STALE'
    finally:
        if _postgres(con):con.connection.close()
        else:con.close()


def purge_terminal(con, *, now, retention_seconds=30*86400, limit=100):
    """Explicit bounded metadata deletion; never removes queued or leased jobs.

    Age is measured from expiry, not issuance. Payloads must already have been
    removed by terminal transitions. This call never recovers leases, sends
    messages, deletes reset tokens or commits the caller's transaction.
    """
    _require(con);now=_time(now)
    if (type(retention_seconds) is not int or not 86400<=retention_seconds<=365*86400
            or type(limit) is not int or not 1<=limit<=1000):
        raise ValueError('QUEUE_RETENTION_CONFIGURATION_REJECTED')
    cutoff=now-retention_seconds
    lock=' FOR UPDATE SKIP LOCKED' if _postgres(con) else ''
    rows=con.execute("""SELECT id FROM reset_mail_queue
        WHERE state IN ('accepted','uncertain','failed','expired')
        AND payload IS NULL AND expires_at<=?
        ORDER BY expires_at,id LIMIT ?"""+lock,(cutoff,limit)).fetchall()
    for row in rows:
        con.execute("""DELETE FROM reset_mail_queue WHERE id=?
            AND state IN ('accepted','uncertain','failed','expired')
            AND payload IS NULL AND expires_at<=?""",(row['id'],cutoff))
    return {'deleted':len(rows)}


def quarantine_restored(con):
    """Offline restored copy only; caller commits alongside token/session revocation.

    A started historical attempt remains uncertain. Other active jobs expire.
    No delivery, recovery or key access occurs. Terminal history is preserved.
    """
    _require(con)
    count=con.execute("""UPDATE reset_mail_queue SET
        state=CASE WHEN state='leased' AND started_at IS NOT NULL
            THEN 'uncertain' ELSE 'expired' END,
        result='RESTORE_QUARANTINED',payload=NULL,owner=NULL,lease_until=NULL,started_at=NULL
        WHERE state IN ('queued','leased')""").rowcount
    return {'quarantined':count}

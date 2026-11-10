"""Disconnected, encrypted SQLite/PostgreSQL REVIEW archive. No HTTP, network or env hooks.

Only receive() may couple a verified event journal with its review ciphertext.
The caller owns the transaction; failures roll back this operation's savepoint
so catching an exception cannot accidentally commit a journal without evidence.
Separate archive keys must be supplied privately by an operator. No defaults.
"""
import hashlib
import hmac
import json
import os
import re
import sqlite3
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from backend import ses_feedback_config
from backend.order_mail_outbox import _require_transaction,_postgres
from backend.sns_pinned_notification import MAX_BODY,json_object

SCHEMA_SQLITE='''
CREATE TABLE IF NOT EXISTS ses_feedback_review (
 event_key TEXT PRIMARY KEY REFERENCES ses_feedback_events(event_key),
 raw_hash TEXT NOT NULL,
 key_id TEXT NOT NULL,
 received_at INTEGER NOT NULL,
 expires_at INTEGER NOT NULL CHECK(expires_at>received_at),
 payload BLOB NOT NULL
);
CREATE INDEX IF NOT EXISTS ses_feedback_review_expiry ON ses_feedback_review(expires_at);
'''


def _aad(row):
    return json.dumps(['ses-feedback-review-v1']+[row[k] for k in
        ('event_key','raw_hash','key_id','received_at','expires_at')],separators=(',',':')).encode()


class ArchiveCipher:
    """Explicit independent AES-256 keys; retain old keys until retention expires."""
    def __init__(self,keys,active):
        if (not isinstance(keys,dict) or not keys or len(keys)>8 or active not in keys or
                any(not isinstance(k,str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,40}',k) or
                    not isinstance(v,bytes) or len(v)!=32 for k,v in keys.items())):
            raise ValueError('SES_REVIEW_KEYS_REJECTED')
        self._keys=dict(keys);self.active=active

    def seal(self,row,raw):
        nonce=os.urandom(12)
        return nonce+AESGCM(self._keys[row['key_id']]).encrypt(nonce,raw,_aad(row))

    def open(self,row):
        """Private operator primitive, never attach to a public API or logs."""
        try:
            payload=bytes(row['payload'])
            if not 28<=len(payload)<=MAX_BODY+28:raise ValueError('Bounded ciphertext required')
            raw=AESGCM(self._keys[row['key_id']]).decrypt(payload[:12],payload[12:],_aad(row))
            if not hmac.compare_digest(hashlib.sha256(raw).hexdigest(),row['raw_hash']):
                raise ValueError('Wrong payload')
            return raw
        except Exception:raise ValueError('SES_REVIEW_DECRYPTION_REJECTED') from None


def _context(con,now):
    _require_transaction(con)
    if (not isinstance(con,sqlite3.Connection) and not _postgres(con)) or type(now) is not int or now<0:
        raise ValueError('SES_REVIEW_CONTEXT_REJECTED')


def purge_expired(con,*,now):
    """Explicit maintenance in caller transaction; no timer or automatic process."""
    _context(con,now)
    return con.execute('DELETE FROM ses_feedback_review WHERE expires_at<=?',(now,)).rowcount


def receive(con,raw,config,cipher,*,now,max_records=1000,retention_seconds=604800):
    """Verify raw SNS, process SES, archive REVIEW atomically; never commits/ACKs.

    A future listener must commit successfully BEFORE responding with success.
    Invalid/stale/unapproved events fail closed, without storing untrusted bodies.
    Applied/ignored events keep only the existing hashed journal. Capacity errors
    must be retried/escalated, never acknowledged as accepted notifications.
    """
    _context(con,now)
    if (not isinstance(cipher,ArchiveCipher) or type(max_records) is not int or
            not 1<=max_records<=10000 or type(retention_seconds) is not int or
            not 3600<=retention_seconds<=2592000):
        raise ValueError('SES_REVIEW_CONTEXT_REJECTED')
    con.execute('SAVEPOINT wp_ses_review')
    try:
        if _postgres(con):
            con.execute("SELECT pg_advisory_xact_lock(hashtextextended('wp:ses-review-capacity',0))")
        result=ses_feedback_config.apply(con,raw,config,now=now)
        if result in ('REVIEW','DUPLICATE'):
            obj=json_object(raw)
            key=hashlib.sha256((obj['TopicArn']+'\n'+obj['MessageId'].lower()).encode()).hexdigest()
            journal=con.execute('SELECT result,received_at FROM ses_feedback_events WHERE event_key=?',(key,)).fetchone()
            existing=con.execute('SELECT event_key FROM ses_feedback_review WHERE event_key=?',(key,)).fetchone()
            if journal['result']!='REVIEW' or existing or journal['received_at']+retention_seconds<=now:
                con.execute('RELEASE SAVEPOINT wp_ses_review')
                return result
            purge_expired(con,now=now)
            if con.execute('SELECT count(*) AS n FROM ses_feedback_review').fetchone()['n']>=max_records:
                raise ValueError('Archive full')
            body=raw.encode('utf-8') if isinstance(raw,str) else raw
            row={'event_key':key,'raw_hash':hashlib.sha256(body).hexdigest(),'key_id':cipher.active,
                 'received_at':journal['received_at'],'expires_at':journal['received_at']+retention_seconds}
            payload=cipher.seal(row,body)
            con.execute('INSERT INTO ses_feedback_review VALUES(?,?,?,?,?,?)',
                tuple(row[k] for k in ('event_key','raw_hash','key_id','received_at','expires_at'))+(payload,))
        con.execute('RELEASE SAVEPOINT wp_ses_review')
        return result
    except Exception:
        con.execute('ROLLBACK TO SAVEPOINT wp_ses_review')
        con.execute('RELEASE SAVEPOINT wp_ses_review')
        raise ValueError('SES_REVIEW_RECEIVE_REJECTED') from None

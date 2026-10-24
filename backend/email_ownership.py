"""Private account email proofs; caller owns transaction and authenticated identity.

No HTTP routes or delivery are enabled by this module. Tokens belong only in a
private mail delivery path, never an HTTP response or log. SES domain validation
is deliberately unrelated to account ownership.
"""
import hashlib
import re
import secrets

from backend.order_mail_outbox import _postgres, _require_transaction, recipient_hash

SCHEMA_SQLITE = '''
CREATE TABLE IF NOT EXISTS account_email_proofs (
 user_id INTEGER PRIMARY KEY REFERENCES users(id),
 email_hash TEXT NOT NULL,
 token_hash TEXT,
 issued_at INTEGER NOT NULL,
 expires_at INTEGER NOT NULL,
 verified_at INTEGER
);
'''
TTL = 900
COOLDOWN = 60


def _time(now):
    if type(now) is not int or now < 0:
        raise ValueError('EMAIL_PROOF_TIME_REJECTED')
    return now


def _user(con, user_id):
    if type(user_id) is not int or user_id < 1:
        raise ValueError('EMAIL_PROOF_OWNER_REJECTED')
    # Serializes issue/consume with the account row; SQLite caller uses BEGIN IMMEDIATE.
    suffix = ' FOR UPDATE' if _postgres(con) else ''
    return con.execute('SELECT id,email FROM users WHERE id=?'+suffix, (user_id,)).fetchone()


def issue(con, user_id, *, now):
    """Authenticated account only. Returns token privately, None on cooldown/proven.

    New issuance invalidates the previous token. Only its SHA256 reaches the DB.
    Caller must commit before passing the token to the private delivery path.
    """
    _require_transaction(con)
    now = _time(now)
    user = _user(con, user_id)
    if not user:
        raise ValueError('EMAIL_PROOF_OWNER_REJECTED')
    current_hash = recipient_hash(user['email'])
    row = con.execute('SELECT * FROM account_email_proofs WHERE user_id=?', (user_id,)).fetchone()
    if row and (now < row['issued_at'] or
                (row['email_hash'] == current_hash and row['verified_at'] is not None) or
                now < row['issued_at'] + COOLDOWN):
        return None
    token = secrets.token_urlsafe(32)
    con.execute('''INSERT INTO account_email_proofs
        (user_id,email_hash,token_hash,issued_at,expires_at,verified_at) VALUES(?,?,?,?,?,NULL)
        ON CONFLICT(user_id) DO UPDATE SET email_hash=excluded.email_hash,
        token_hash=excluded.token_hash,issued_at=excluded.issued_at,
        expires_at=excluded.expires_at,verified_at=NULL''',
        (user_id,current_hash,hashlib.sha256(token.encode()).hexdigest(),now,now+TTL))
    return token


def consume(con, user_id, token, *, now):
    """Authenticated user + secret required; single-use and current-address bound."""
    _require_transaction(con)
    now = _time(now)
    user = _user(con, user_id)
    if not user or not isinstance(token,str) or not re.fullmatch(r'[A-Za-z0-9_-]{43}',token):
        return False
    row = con.execute('SELECT * FROM account_email_proofs WHERE user_id=?', (user_id,)).fetchone()
    if (not row or row['verified_at'] is not None or not row['token_hash'] or
            not row['issued_at'] <= now < row['expires_at'] or
            row['email_hash'] != recipient_hash(user['email']) or
            not secrets.compare_digest(row['token_hash'],hashlib.sha256(token.encode()).hexdigest())):
        return False
    con.execute('UPDATE account_email_proofs SET verified_at=?,token_hash=NULL WHERE user_id=?',
                (now,user_id))
    return True


def verified_recipient(con, user_id, email):
    """Trusted outbox callback. Checks proof AND current stored address, never UI flags."""
    user = con.execute('SELECT email FROM users WHERE id=?', (user_id,)).fetchone()
    if not user:
        return False
    expected = recipient_hash(user['email'])
    if recipient_hash(email) != expected:
        return False
    row = con.execute('SELECT email_hash,verified_at FROM account_email_proofs WHERE user_id=?',
                      (user_id,)).fetchone()
    return bool(row and row['verified_at'] is not None and row['email_hash'] == expected)

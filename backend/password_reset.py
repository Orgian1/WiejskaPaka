"""Opt-in SQLite demo reset; real delivery must use a verified external channel."""
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import stat

from backend.time_safety import utc_datetime
from backend.notification_policy import Event, Channel, validate_channel

SCHEMA_SQLITE = '''
CREATE TABLE IF NOT EXISTS password_reset_tokens (
    token_hash TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    password_version TEXT NOT NULL,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS password_reset_owner ON password_reset_tokens(user_id);
CREATE TABLE IF NOT EXISTS password_reset_limits (
    bucket TEXT PRIMARY KEY,
    attempts INTEGER NOT NULL CHECK(attempts > 0),
    window_started_at TEXT NOT NULL
);
'''
WINDOW = timedelta(minutes=15)
NOTICE = 'Jeśli adres jest przypisany do konta, otrzymasz instrukcję zmiany hasła.'
INVALID = 'Link jest nieprawidłowy, wykorzystany lub wygasł. Poproś o nowy.'


def digest(value):
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


def budget(con, bucket, limit, now):
    row = con.execute('SELECT attempts,window_started_at FROM password_reset_limits WHERE bucket=?',
                      (bucket,)).fetchone()
    start = utc_datetime(row['window_started_at']) if row else now
    if start > now:
        return False
    active = row is not None and now < start + WINDOW
    if active and row['attempts'] >= limit:
        return False
    con.execute('''INSERT INTO password_reset_limits VALUES(?,?,?)
        ON CONFLICT(bucket) DO UPDATE SET attempts=excluded.attempts,
        window_started_at=excluded.window_started_at''',
        (bucket, row['attempts']+1 if active else 1, (start if active else now).isoformat()))
    return True


def issue(con, email, *, now=None):
    """Caller holds BEGIN IMMEDIATE and commits rate counters even on denial.

    Returns an unbound random token for unknown emails, so the demo mailbox
    and HTTP response do not disclose registration. Only hashes enter SQLite.
    """
    now = now or datetime.now(timezone.utc)
    email = email.strip().lower()
    con.execute('DELETE FROM password_reset_tokens WHERE expires_at<=?', (now.isoformat(),))
    con.execute('DELETE FROM password_reset_limits WHERE window_started_at<=?',
                ((now-WINDOW).isoformat(),))
    # Global cap bounds both disk deliveries and attacker-selected bucket rows.
    if not budget(con, 'issue:global', 100, now):
        return None
    if not budget(con, 'issue:'+digest(email), 3, now):
        return None
    token = secrets.token_urlsafe(32)
    user = con.execute('SELECT id,password_hash FROM users WHERE email=?', (email,)).fetchone()
    if user:
        con.execute('INSERT INTO password_reset_tokens VALUES(?,?,?,?,?)',
                    (digest(token), user['id'], digest(user['password_hash']),
                     now.isoformat(), (now+WINDOW).isoformat()))
    return token


def consume(con, hasher, token, new_password, *, now=None):
    """Atomically consume all reset links, replace password, revoke all sessions."""
    now = now or datetime.now(timezone.utc)
    if not budget(con, 'consume:global', 100, now):
        return 429
    if not re.fullmatch(r'[A-Za-z0-9_-]{43}', token):
        return 400
    row = con.execute('''SELECT r.*,u.password_hash,u.email FROM password_reset_tokens r
        JOIN users u ON u.id=r.user_id WHERE r.token_hash=?''', (digest(token),)).fetchone()
    if (not row or utc_datetime(row['created_at']) > now
            or utc_datetime(row['expires_at']) <= now
            or not secrets.compare_digest(row['password_version'], digest(row['password_hash']))):
        return 400
    con.execute('UPDATE users SET password_hash=? WHERE id=?', (hasher.hash(new_password), row['user_id']))
    con.execute('DELETE FROM sessions WHERE user_id=?', (row['user_id'],))
    con.execute('DELETE FROM password_reset_tokens WHERE user_id=?', (row['user_id'],))
    con.execute('DELETE FROM login_attempts WHERE email=?', (row['email'],))
    return 200


def prepare_outbox(folder):
    folder = Path(folder)
    if folder.is_symlink():
        raise ValueError('Nieprawidłowa skrzynka testowa')
    folder.mkdir(mode=0o700, exist_ok=True)
    info = folder.stat()
    if not stat.S_ISDIR(info.st_mode) or (os.name == 'posix' and
            (info.st_uid != os.getuid() or info.st_mode & 0o077)):
        raise ValueError('Nieprawidłowe uprawnienia skrzynki testowej')
    return folder


def deliver_demo(folder, email, token):
    """Private local test mailbox; never expose token through API or server log."""
    validate_channel(Event.PASSWORD_RESET, Channel.EMAIL, email_verified=False)
    folder = prepare_outbox(folder)
    path = folder / (secrets.token_hex(16)+'.json')
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump({'recipient': email.strip().lower(), 'fragment': '#reset-token='+token,
                       'test_only': True}, stream)
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        path.unlink(missing_ok=True)
        raise
    return path

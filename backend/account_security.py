"""Local password change with a persistent, account-wide reauthentication budget."""
from datetime import datetime,timedelta,timezone
from argon2.exceptions import VerificationError,InvalidHashError
from backend.time_safety import utc_datetime

SCHEMA_SQLITE='''
CREATE TABLE IF NOT EXISTS password_change_access (
    user_id INTEGER PRIMARY KEY REFERENCES users(id),
    attempts INTEGER NOT NULL CHECK(attempts BETWEEN 1 AND 5),
    window_started_at TEXT NOT NULL
);
'''


class AccountChangeError(ValueError):
    def __init__(self,status,message,headers=None):
        super().__init__(message);self.status,self.headers=status,headers


def change_password(con,hasher,user_id,current_password,new_password,*,now=None):
    """Caller locks with login, reauthenticates, and commits expected denials."""
    now=now or datetime.now(timezone.utc);window=timedelta(minutes=15)
    row=con.execute('SELECT attempts,window_started_at FROM password_change_access WHERE user_id=?',(user_id,)).fetchone()
    start=utc_datetime(row['window_started_at']) if row else now
    if start>now or (row and now<start+window and row['attempts']>=5):
        remaining=start+window-now
        seconds=min(900,max(1,remaining.days*86400+remaining.seconds+(1 if remaining.microseconds else 0)))
        raise AccountChangeError(429,'Zbyt wiele prób zmiany hasła. Spróbuj później.',{'Retry-After':str(seconds)})
    active=now<start+window
    count=row['attempts']+1 if row and active else 1
    con.execute('''INSERT INTO password_change_access(user_id,attempts,window_started_at)
        VALUES(?,?,?) ON CONFLICT(user_id) DO UPDATE SET
        attempts=excluded.attempts,window_started_at=excluded.window_started_at''',
        (user_id,count,(start if active else now).isoformat()))
    row=con.execute('SELECT password_hash FROM users WHERE id=?',(user_id,)).fetchone()
    try:valid=row is not None and hasher.verify(row['password_hash'],current_password)
    except (VerificationError,InvalidHashError):valid=False
    if not valid:raise AccountChangeError(401,'Nieprawidłowe obecne hasło.')
    if current_password==new_password:raise AccountChangeError(422,'Nowe hasło musi różnić się od obecnego.')
    encoded=hasher.hash(new_password)
    con.execute('UPDATE users SET password_hash=? WHERE id=?',(encoded,user_id))
    con.execute('DELETE FROM sessions WHERE user_id=?',(user_id,))
    return {'changed':True,'reauthentication_required':True}

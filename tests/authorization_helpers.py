"""Real disposable bearer sessions for existing synthetic accounting fixtures."""
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from backend import app as api


def authorization_for(user):
    token = uuid4().hex
    with api.db() as con:
        row = con.execute('SELECT role FROM users WHERE id=?', (user['id'],)).fetchone()
        assert row is not None and row['role'] == user['role'], 'Inconsistent synthetic actor'
        con.execute('INSERT INTO sessions(token_hash,user_id,expires_at) VALUES(?,?,?)',
                    (api.token_hash(token), user['id'],
                     (datetime.now(timezone.utc)+timedelta(hours=1)).isoformat()))
    return 'Bearer ' + token

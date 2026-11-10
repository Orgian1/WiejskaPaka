"""Minimal account-scoped session overview; never return tokens or their hashes."""
from datetime import datetime,timezone
from backend.neon_auth_policy import active_session
from backend.time_safety import utc_datetime


class SessionInactiveError(ValueError):
    pass


def session_overview(con,user_id,current_hash,*,now=None):
    now=now or datetime.now(timezone.utc)
    rows=con.execute('SELECT token_hash,expires_at FROM sessions WHERE user_id=?',(user_id,)).fetchall()
    live=[r for r in rows if active_session(user_id,r['expires_at'],now)]
    current=next((r for r in live if r['token_hash']==current_hash),None)
    if current is None:raise SessionInactiveError('Current session is inactive')
    return {'active_sessions':len(live),'other_sessions':len(live)-1,
            'current_expires_at':utc_datetime(current['expires_at']).isoformat()}


def revoke_other_sessions(con,user_id,current_hash):
    # Defense in depth: a caller must not revoke sessions with a stale or
    # foreign token, even if it bypasses the HTTP transaction guard.
    session_overview(con,user_id,current_hash)
    # Remove expired rows as well; they are not counted as active sessions.
    con.execute('DELETE FROM sessions WHERE user_id=? AND token_hash<>?',(user_id,current_hash))
    return {'ok':True,'other_sessions':0}

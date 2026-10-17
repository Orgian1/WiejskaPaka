from datetime import datetime, timedelta, timezone
from backend.neon_auth_policy import active_session, actor_role, normalize_expiry
from backend.neon_session_bridge import authenticate_session, AuthenticationFailed
import pytest

NOW = datetime(2026, 10, 14, tzinfo=timezone.utc)

@pytest.mark.parametrize('expiry', [NOW + timedelta(seconds=1), (NOW + timedelta(seconds=1)).isoformat(), '2026-10-14T00:00:01Z'])
def test_expiry_valid_formats(expiry):
    assert normalize_expiry(expiry) is not None

def test_expired_and_invalid_rejected():
    for expiry in [NOW, NOW - timedelta(seconds=1), 'bad', None, datetime(2027, 1, 1)]:
        assert not active_session(2, expiry, NOW)
    assert not active_session(True, NOW + timedelta(days=1), NOW)
    assert not active_session(0, NOW + timedelta(days=1), NOW)

class Conn:
    def __init__(self, row): self.row = row; self.calls = []
    def execute(self, sql, params):
        self.calls.append((sql, params))
        return self
    def fetchone(self): return self.row

def test_role_checked_from_database_not_input():
    c = Conn({'role': 'rolnik'})
    assert actor_role(c, 8, ('rolnik',)) == 'rolnik'
    assert actor_role(c, 8, ('klient',)) is None
    assert c.calls[0][1] == (8,)

def test_missing_and_unknown_role_fail_closed():
    assert actor_role(Conn(None), 8, ('rolnik',)) is None
    assert actor_role(Conn({'role': 'administrator'}), 8, ('admin',)) is None
    with pytest.raises(ValueError): actor_role(Conn(None), 8, ('unknown',))

def test_session_checks_expiry_and_parameterizes_hash():
    c = Conn({'user_id': 7, 'expires_at': NOW + timedelta(minutes=1)})
    assert authenticate_session(c, 'Bearer safe-token', now=NOW) == 7
    assert 'safe-token' not in c.calls[0][0]
    assert 'safe-token' not in repr(c.calls[0][1])
    with pytest.raises(AuthenticationFailed):
        authenticate_session(Conn({'user_id': 7, 'expires_at': NOW}), 'Bearer safe-token', now=NOW)

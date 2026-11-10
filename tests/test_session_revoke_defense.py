"""Low-level session revocation must not trust a caller-supplied account id."""
import pytest
from backend import app as api
from backend.session_security import revoke_other_sessions, SessionInactiveError
from tests.test_account_security_api import account


def test_revoke_helper_denies_foreign_or_nonexistent_current_token():
    client, headers, user_id, _, extra = account()
    other, other_headers, other_id, *_ = account()
    with api.db() as con:
        before = con.execute('SELECT COUNT(*) FROM sessions WHERE user_id=?', (user_id,)).fetchone()[0]
        with pytest.raises(SessionInactiveError):
            revoke_other_sessions(con, user_id, api.token_hash(other_headers['Authorization'][7:]))
        with pytest.raises(SessionInactiveError):
            revoke_other_sessions(con, user_id, 'not-a-session')
        after = con.execute('SELECT COUNT(*) FROM sessions WHERE user_id=?', (user_id,)).fetchone()[0]
    assert before == after == 2
    assert client.get('/auth/me', headers=extra).status_code == 200
    assert other.get('/auth/me', headers=other_headers).status_code == 200


def test_revoke_helper_denies_expired_current_session_without_deleting_others():
    client, headers, user_id, _, extra = account()
    current_hash = api.token_hash(headers['Authorization'][7:])
    with api.db() as con:
        con.execute('UPDATE sessions SET expires_at=? WHERE token_hash=?', ('2000-01-01T00:00:00Z', current_hash))
        with pytest.raises(SessionInactiveError):
            revoke_other_sessions(con, user_id, current_hash)
        assert con.execute('SELECT COUNT(*) FROM sessions WHERE user_id=?', (user_id,)).fetchone()[0] == 2
    assert client.get('/auth/me', headers=extra).status_code == 200

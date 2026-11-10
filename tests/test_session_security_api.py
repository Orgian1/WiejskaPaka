"""Account session controls deny stale requests and expose no credentials."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timedelta,timezone
from uuid import uuid4
import pytest
from fastapi import Header
from fastapi.testclient import TestClient
from backend import app as api
from tests.test_account_security_api import account,OLD,NEW,change
from tests.test_b10921_security_boundaries import actor

ROUTES=[('get','/auth/sessions'),('post','/auth/logout'),('post','/auth/logout-all'),('post','/auth/logout-others')]


@pytest.mark.parametrize('role',['klient','rolnik','dostawca','admin'])
def test_overview_and_revoke_other_sessions_are_private_and_account_scoped(role):
    c,h,uid,email,extra=account(role);stranger,_=actor('klient')
    r=c.get('/auth/sessions',headers=h);assert r.status_code==200,r.text
    assert r.headers['cache-control']=='no-store'
    data=r.json();assert set(data)=={'active_sessions','other_sessions','current_expires_at'}
    assert data['active_sessions']==2 and data['other_sessions']==1
    for secret in (email,h['Authorization'][7:],extra['Authorization'][7:],api.token_hash(h['Authorization'][7:])):assert secret not in r.text
    assert c.post('/auth/logout-others',headers=h).json()=={'ok':True,'other_sessions':0}
    assert c.get('/auth/me',headers=h).status_code==200
    assert c.get('/auth/me',headers=extra).status_code==401
    assert c.get('/auth/me',headers=stranger).status_code==200
    assert c.get('/auth/sessions',headers=h).json()['active_sessions']==1
    assert c.post('/auth/logout-others',headers=h).status_code==200
    # A fresh login is allowed. Revocation is not a password change.
    new=c.post('/auth/login',json={'email':email,'password':OLD});assert new.status_code==200
    assert c.get('/auth/sessions',headers=h).json()['other_sessions']==1


@pytest.mark.parametrize('expiry',['2000-01-01T00:00:00Z','2100-01-01T00:00:00','invalid','',None])
def test_overview_counts_only_valid_active_timestamps_without_deleting_rows(expiry):
    c,h,uid,*_=account()
    with api.db() as con:
        con.execute('UPDATE sessions SET expires_at=? WHERE user_id=? AND token_hash<>?',
                    (expiry if expiry is not None else 'not-a-date',uid,api.token_hash(h['Authorization'][7:])))
        before=[tuple(r) for r in con.execute('SELECT * FROM sessions WHERE user_id=? ORDER BY token_hash',(uid,))]
    r=c.get('/auth/sessions',headers=h);assert r.status_code==200,r.text
    assert r.json()['active_sessions']==1 and r.json()['other_sessions']==0
    with api.db() as con:assert before==[tuple(r) for r in con.execute('SELECT * FROM sessions WHERE user_id=? ORDER BY token_hash',(uid,))]


def test_overview_normalizes_offsets_instead_of_lexical_comparison():
    c,h,uid,*_=account()
    expiry=(datetime.now(timezone.utc)+timedelta(hours=2)).astimezone(timezone(timedelta(hours=-10))).isoformat()
    with api.db() as con:con.execute('UPDATE sessions SET expires_at=? WHERE user_id=?',(expiry,uid))
    r=c.get('/auth/sessions',headers=h);assert r.json()['active_sessions']==2
    assert r.json()['current_expires_at'].endswith('+00:00')


@pytest.mark.parametrize('method,url',ROUTES)
@pytest.mark.parametrize('change_kind',['logout','expire','role'])
def test_all_session_controls_recheck_after_dependency_snapshot(method,url,change_kind):
    c,h,uid,*_=account()
    def stale(authorization: str | None=Header(default=None)):
        user=api.current_user(authorization)
        with api.db() as con:
            if change_kind=='logout':con.execute('DELETE FROM sessions WHERE token_hash=?',(api.token_hash(authorization[7:]),))
            elif change_kind=='expire':con.execute('UPDATE sessions SET expires_at=? WHERE token_hash=?',('2000-01-01T00:00:00Z',api.token_hash(authorization[7:])))
            else:con.execute('UPDATE users SET role=? WHERE id=?',('dostawca',uid))
        return user
    api.app.dependency_overrides[api.current_user]=stale
    try:r=getattr(c,method)(url,headers=h)
    finally:api.app.dependency_overrides.pop(api.current_user,None)
    assert r.status_code==(403 if change_kind=='role' else 401),r.text
    with api.db() as con:assert con.execute('SELECT COUNT(*) FROM sessions WHERE user_id=? AND token_hash<>?',(uid,api.token_hash(h['Authorization'][7:]))).fetchone()[0]==1


@pytest.mark.parametrize('method,url',ROUTES)
def test_session_controls_require_valid_bearer(method,url):
    c=TestClient(api.app)
    for headers in ({},{'Authorization':'Bearer unknown'},{'Authorization':'Bearer bad token'},{'Authorization':'Basic token'}):
        assert getattr(c,method)(url,headers=headers).status_code==401


@pytest.mark.parametrize('url',['/auth/logout','/auth/logout-all','/auth/logout-others'])
def test_delete_failure_rolls_back_and_returns_generic_error(url):
    c,h,uid,*_=account()
    with api.db() as con:con.execute(f"CREATE TRIGGER fail_session_delete BEFORE DELETE ON sessions WHEN OLD.user_id={uid} BEGIN SELECT RAISE(ABORT,'PRIVATE-SESSION-FAILURE'); END")
    try:r=TestClient(api.app,raise_server_exceptions=False).post(url,headers=h)
    finally:
        with api.db() as con:con.execute('DROP TRIGGER fail_session_delete')
    assert r.status_code==500 and 'PRIVATE-SESSION-FAILURE' not in r.text
    assert c.get('/auth/sessions',headers=h).json()['active_sessions']==2


def test_two_devices_revoking_each_other_have_one_winner():
    c,h,uid,email,extra=account()
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(lambda header:c.post('/auth/logout-others',headers=header),[h,extra]))
    assert sorted(r.status_code for r in results)==[200,401]
    assert sorted(c.get('/auth/me',headers=x).status_code for x in [h,extra])==[200,401]
    with api.db() as con:assert con.execute('SELECT COUNT(*) FROM sessions WHERE user_id=?',(uid,)).fetchone()[0]==1


def test_password_change_and_other_session_revocation_cannot_leave_old_tokens():
    c,h,uid,email,extra=account()
    with ThreadPoolExecutor(max_workers=2) as pool:
        f=pool.submit(change,c,h);g=pool.submit(c.post,'/auth/logout-others',headers=h)
        changed,revoked=f.result(),g.result()
    assert changed.status_code==200 and revoked.status_code in (200,401)
    assert all(c.get('/auth/me',headers=x).status_code==401 for x in [h,extra])
    assert c.post('/auth/login',json={'email':email,'password':NEW}).status_code==200


def test_current_logout_preserves_other_sessions_and_logout_all_is_account_scoped():
    c,h,uid,email,extra=account();stranger,_=actor('klient')
    assert c.post('/auth/logout',headers=h).status_code==200
    assert c.get('/auth/me',headers=h).status_code==401
    assert c.get('/auth/me',headers=extra).status_code==200
    assert c.post('/auth/logout-all',headers=extra).status_code==200
    assert c.get('/auth/me',headers=extra).status_code==401
    assert c.get('/auth/me',headers=stranger).status_code==200


def test_expiry_between_authorization_and_snapshot_is_401_not_server_error(monkeypatch):
    from backend import session_security
    c,h,uid,*_=account();real=session_security.session_overview
    def later(con,user_id,digest):
        return real(con,user_id,digest,now=datetime.now(timezone.utc)+timedelta(days=30))
    monkeypatch.setattr(session_security,'session_overview',later)
    assert c.get('/auth/sessions',headers=h).status_code==401
    assert c.get('/auth/me',headers=h).status_code==200

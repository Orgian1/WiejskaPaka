"""Password changes are atomic, reauthenticated and revoke every old session."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timedelta,timezone
from uuid import uuid4
import pytest
from fastapi import Header
from fastapi.testclient import TestClient
from backend import app as api
from tests.test_b10921_security_boundaries import actor

OLD='Old-private-synthetic-password!'
NEW='New-private-synthetic-password!'


def account(role='klient'):
    headers,uid=actor(role)
    with api.db() as con:
        con.execute('UPDATE users SET password_hash=? WHERE id=?',(api.ph.hash(OLD),uid))
        email=con.execute('SELECT email FROM users WHERE id=?',(uid,)).fetchone()[0]
        extra=uuid4().hex
        con.execute('INSERT INTO sessions(token_hash,user_id,expires_at) VALUES(?,?,?)',
            (api.token_hash(extra),uid,(datetime.now(timezone.utc)+timedelta(hours=1)).isoformat()))
    return TestClient(api.app),headers,uid,email,{'Authorization':'Bearer '+extra}


def change(c,h,old=OLD,new=NEW):return c.post('/auth/change-password',headers=h,json={'current_password':old,'new_password':new})


@pytest.mark.parametrize('role',['klient','rolnik','dostawca','admin'])
def test_change_requires_password_and_revokes_all_own_sessions_only(role):
    c,h,uid,email,extra=account(role);other,_=actor('klient')
    r=change(c,h);assert r.status_code==200,r.text
    assert r.json()=={'changed':True,'reauthentication_required':True}
    assert r.headers['cache-control']=='no-store'
    for old in (h,extra):assert c.get('/auth/me',headers=old).status_code==401
    assert c.get('/auth/me',headers=other).status_code==200
    with api.db() as con:
        row=con.execute('SELECT password_hash FROM users WHERE id=?',(uid,)).fetchone()
        assert row[0] not in (NEW,OLD) and row[0].startswith('$argon2id$') and api.ph.verify(row[0],NEW)
        assert con.execute('SELECT COUNT(*) FROM sessions WHERE user_id=?',(uid,)).fetchone()[0]==0
    assert c.post('/auth/login',json={'email':email,'password':OLD}).status_code==401
    assert c.post('/auth/login',json={'email':email,'password':NEW}).status_code==200


@pytest.mark.parametrize('change_kind',['logout','expire','role'])
def test_change_reauthenticates_after_dependency_snapshot(change_kind):
    c,h,uid,*_=account()
    def stale(authorization: str | None=Header(default=None)):
        user=api.current_user(authorization)
        with api.db() as con:
            if change_kind=='logout':con.execute('DELETE FROM sessions WHERE user_id=?',(uid,))
            elif change_kind=='expire':con.execute('UPDATE sessions SET expires_at=? WHERE user_id=?',('2000-01-01T00:00:00+00:00',uid))
            else:con.execute('UPDATE users SET role=? WHERE id=?',('rolnik',uid))
        return user
    api.app.dependency_overrides[api.current_user]=stale
    try:r=change(c,h)
    finally:api.app.dependency_overrides.pop(api.current_user,None)
    assert r.status_code==(403 if change_kind=='role' else 401)
    with api.db() as con:assert api.ph.verify(con.execute('SELECT password_hash FROM users WHERE id=?',(uid,)).fetchone()[0],OLD)


def test_failed_password_counter_is_committed_and_shared_across_tokens_then_resets():
    c,h,uid,email,extra=account()
    for _ in range(5):
        r=change(c,h,old='wrong');assert r.status_code==401
        assert c.get('/auth/me',headers=h).status_code==200
    limited=change(c,extra)
    assert limited.status_code==429 and 1<=int(limited.headers['retry-after'])<=900
    with api.db() as con:
        assert con.execute('SELECT attempts FROM password_change_access WHERE user_id=?',(uid,)).fetchone()[0]==5
        con.execute('UPDATE password_change_access SET window_started_at=? WHERE user_id=?',
            ((datetime.now(timezone.utc)-timedelta(minutes=16)).isoformat(),uid))
    assert change(c,extra).status_code==200


def test_concurrent_changes_only_one_wins_and_neither_leaves_old_tokens_alive():
    c,h,uid,email,extra=account();passwords=[NEW+'-1',NEW+'-2']
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(lambda new:change(c,h,new=new),passwords))
    assert sorted(r.status_code for r in results)==[200,401]
    successful=passwords[next(i for i,r in enumerate(results) if r.status_code==200)]
    with api.db() as con:
        assert api.ph.verify(con.execute('SELECT password_hash FROM users WHERE id=?',(uid,)).fetchone()[0],successful)
        assert con.execute('SELECT COUNT(*) FROM sessions WHERE user_id=?',(uid,)).fetchone()[0]==0


@pytest.mark.parametrize('failure',['hash','delete'])
def test_storage_failure_rolls_back_hash_sessions_and_counter(monkeypatch,failure):
    c,h,uid,email,extra=account()
    with api.db() as con:before=con.execute('SELECT password_hash FROM users WHERE id=?',(uid,)).fetchone()[0]
    def fail(*_a,**_k):raise RuntimeError('PRIVATE-PASSWORD-FAILURE')
    if failure=='delete':
        with api.db() as con:con.execute(f"CREATE TRIGGER fail_password_delete BEFORE DELETE ON sessions WHEN OLD.user_id={uid} BEGIN SELECT RAISE(ABORT,'PRIVATE-PASSWORD-FAILURE'); END")
    try:
        with monkeypatch.context() as patch:
            if failure=='hash':
                class FailingHasher:
                    verify=staticmethod(api.ph.verify)
                    hash=staticmethod(fail)
                patch.setattr(api,'ph',FailingHasher())
            r=TestClient(api.app,raise_server_exceptions=False).post('/auth/change-password',headers=h,json={'current_password':OLD,'new_password':NEW})
    finally:
        if failure=='delete':
            with api.db() as con:con.execute('DROP TRIGGER fail_password_delete')
    assert r.status_code==500 and 'PRIVATE-PASSWORD-FAILURE' not in r.text
    with api.db() as con:
        assert con.execute('SELECT password_hash FROM users WHERE id=?',(uid,)).fetchone()[0]==before
        assert con.execute('SELECT COUNT(*) FROM sessions WHERE user_id=?',(uid,)).fetchone()[0]==2
        assert con.execute('SELECT attempts FROM password_change_access WHERE user_id=?',(uid,)).fetchone() is None


@pytest.mark.parametrize('body',[
 {},{'current_password':OLD,'new_password':'x'*11},{'current_password':OLD,'new_password':'x'*257},
 {'current_password':'x'*257,'new_password':NEW},{'current_password':OLD,'new_password':123},
 {'current_password':OLD,'new_password':NEW,'user_id':1},
])
def test_validation_is_bounded_strict_and_never_echoes_passwords(body):
    c,h,*_=account();r=c.post('/auth/change-password',headers=h,json=body)
    assert r.status_code==422 and OLD not in r.text and NEW not in r.text and 'x'*257 not in r.text


def test_same_password_is_denied_without_mutation():
    c,h,uid,*_=account();assert change(c,h,new=OLD).status_code==422
    assert c.get('/auth/me',headers=h).status_code==200


@pytest.mark.parametrize('password',['z'*12,'  Nowe-hasło-zażółć!  '])
def test_new_password_preserves_exact_unicode_and_space_characters(password):
    c,h,uid,email,extra=account();assert change(c,h,new=password).status_code==200
    assert c.post('/auth/login',json={'email':email,'password':password}).status_code==200


def test_no_session_and_corrupt_hash_never_change_account():
    c,h,uid,*_=account();assert change(c,{}).status_code==401
    with api.db() as con:con.execute('UPDATE users SET password_hash=? WHERE id=?',('invalid',uid))
    assert change(c,h).status_code==401

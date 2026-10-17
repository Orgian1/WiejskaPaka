"""Storage secrecy, AAD isolation, key lifecycle and real checkout contracts."""
import json
import os
from pathlib import Path
import secrets
import sqlite3
from datetime import datetime,timedelta,timezone
from concurrent.futures import ThreadPoolExecutor
import pytest
from backend.checkout_vault import (Vault,create_ring,read_ring,rotate_ring,initialize,sweep,CheckoutStorageError,b64)

NOW=datetime(2026,10,16,10,0,tzinfo=timezone.utc)
RESPONSE={'id':21,'pickup_code':'WP-SYNTHETIC','pin_test_only':'012345','total_grosze':799}


def vault(tmp_path):
    active,keys=create_ring(tmp_path/'private.checkout-key');return Vault(active,keys)


def store():
    c=sqlite3.connect(':memory:');c.row_factory=sqlite3.Row
    c.execute('CREATE TABLE checkout_idempotency(buyer_id INTEGER,request_key TEXT,payload_hash TEXT,response_json TEXT,created_at TEXT,PRIMARY KEY(buyer_id,request_key))')
    return c


def test_no_plaintext_pin_or_response_and_fresh_nonce(tmp_path):
    v=vault(tmp_path);until=(NOW+timedelta(days=1)).isoformat()
    a=v.seal(RESPONSE,2,'request-key','payload',pin_until=until);b=v.seal(RESPONSE,2,'request-key','payload',pin_until=until)
    assert a!=b and all(s not in a for s in ('012345','pin_test_only','WP-SYNTHETIC','total_grosze'))
    assert v.open(a,2,'request-key','payload',now=NOW)==RESPONSE
    assert v.open(b,2,'request-key','payload',now=NOW)==RESPONSE


@pytest.mark.parametrize('field,value',[
 ('buyer',3),('request','another-key'),('payload','different-payload'),
 ('key_id','missing-key'),('pin_until','2099-01-01T00:00:00+00:00'),
 ('pin_state','redacted'),('nonce',b64(b'0'*12)),('ciphertext',b64(b'changed')),
 ('format','unsupported'),
])
def test_ciphertext_cannot_be_moved_or_modified(tmp_path,field,value):
    v=vault(tmp_path);raw=v.seal(RESPONSE,2,'request-key','payload',pin_until=(NOW+timedelta(days=1)).isoformat())
    args=[2,'request-key','payload']
    if field in ('buyer','request','payload'):args[('buyer','request','payload').index(field)]=value
    else:
        envelope=json.loads(raw);envelope[field]=value;raw=json.dumps(envelope)
    with pytest.raises(CheckoutStorageError):v.open(raw,*args,now=NOW)


@pytest.mark.parametrize('delta,available',[(timedelta(seconds=-1),True),(timedelta(0),False),(timedelta(days=1),False)])
def test_exact_pin_deadline(tmp_path,delta,available):
    v=vault(tmp_path);raw=v.seal(RESPONSE,2,'key','payload',pin_until=NOW.isoformat())
    result=v.open(raw,2,'key','payload',now=NOW+delta)
    assert ('pin_test_only' in result)==available and result['id']==21
    if not available:assert result['pin_available'] is False


def test_reconciliation_never_reveals_pin_even_with_live_secret(tmp_path):
    v=vault(tmp_path);raw=v.seal(RESPONSE,2,'key','payload',pin_until=(NOW+timedelta(days=1)).isoformat())
    assert 'pin_test_only' not in v.open(raw,2,'key','payload',now=NOW,expose_pin=False)


def test_sweep_removes_secret_but_preserves_identity_and_idempotency(tmp_path):
    v=vault(tmp_path);c=store();raw=v.seal(RESPONSE,2,'key','payload',pin_until=NOW.isoformat())
    c.execute('INSERT INTO checkout_idempotency VALUES(?,?,?,?,?)',(2,'key','payload',raw,(NOW-timedelta(days=1)).isoformat()))
    assert sweep(c,v,now=NOW)==1
    current=c.execute('SELECT response_json FROM checkout_idempotency').fetchone()[0]
    decoded,envelope=v._decrypt(current,2,'key','payload')
    assert 'pin_test_only' not in decoded and decoded['id']==21
    assert envelope['pin_state']=='redacted' and decoded['pin_available'] is False
    assert sweep(c,v,now=NOW+timedelta(days=1))==0
    assert v.open(current,2,'key','payload',now=NOW)==decoded


@pytest.mark.parametrize('old',[False,True])
def test_legacy_plaintext_migration_obeys_original_age(tmp_path,old):
    c=store();created=NOW-timedelta(days=2) if old else NOW
    c.execute('INSERT INTO checkout_idempotency VALUES(?,?,?,?,?)',(2,'key','payload',json.dumps(RESPONSE),created.isoformat()))
    v,changed=initialize(c,tmp_path/'db.sqlite3',now=NOW)
    assert changed==1
    raw=c.execute('SELECT response_json FROM checkout_idempotency').fetchone()[0]
    assert 'pin_test_only' not in raw and '012345' not in raw
    decoded=v.open(raw,2,'key','payload',now=NOW)
    assert ('pin_test_only' in decoded)==(not old)
    assert initialize(c,tmp_path/'db.sqlite3',now=NOW)[1]==0


def test_missing_key_for_existing_ciphertext_fails_without_replacement(tmp_path):
    c=store();v=vault(tmp_path)
    raw=v.seal(RESPONSE,2,'key','payload',pin_until=NOW.isoformat())
    c.execute('INSERT INTO checkout_idempotency VALUES(?,?,?,?,?)',(2,'key','payload',raw,NOW.isoformat()))
    with pytest.raises(CheckoutStorageError):initialize(c,tmp_path/'missing.sqlite3',now=NOW)
    assert not (tmp_path/'missing.sqlite3.checkout-key').exists()
    assert c.execute('SELECT response_json FROM checkout_idempotency').fetchone()[0]==raw


def test_postgres_never_silently_creates_a_local_key(tmp_path):
    class Connection:
        def execute(self,*args):return self
        def fetchall(self):return []
    with pytest.raises(CheckoutStorageError):initialize(Connection(),tmp_path/'db',postgres=True,now=NOW)
    assert list(tmp_path.iterdir())==[]


@pytest.mark.parametrize('kind',['symlink','directory','permissions'])
def test_reject_unsafe_key_file(tmp_path,kind):
    key=tmp_path/'safe.checkout-key';create_ring(key)
    if kind=='symlink':target=tmp_path/'link.checkout-key';target.symlink_to(key)
    elif kind=='directory':target=tmp_path
    else:key.chmod(0o644);target=key
    with pytest.raises((OSError,CheckoutStorageError)):read_ring(target)


def test_concurrent_key_creation_uses_one_complete_key(tmp_path):
    path=tmp_path/'shared.checkout-key'
    with ThreadPoolExecutor(max_workers=8) as pool:rings=list(pool.map(lambda _:create_ring(path),range(16)))
    assert all(r==rings[0] for r in rings)
    assert path.stat().st_mode&0o777==0o600
    assert len(list(tmp_path.iterdir()))==1


def test_rotation_keeps_old_replies_readable_and_uses_new_key(tmp_path):
    path=tmp_path/'private.checkout-key';old=vault(tmp_path)
    raw=old.seal(RESPONSE,2,'key','payload',pin_until=(NOW+timedelta(days=1)).isoformat())
    new_id=rotate_ring(path);active,keys=read_ring(path);new=Vault(active,keys)
    assert new_id==active and active!=old.active and len(keys)==2
    assert new.open(raw,2,'key','payload',now=NOW)==RESPONSE
    fresh=new.seal(RESPONSE,2,'key','payload',pin_until=(NOW+timedelta(days=1)).isoformat())
    assert json.loads(fresh)['key_id']==new_id
    with pytest.raises(CheckoutStorageError):old.open(fresh,2,'key','payload',now=NOW)


def test_migration_failure_can_be_rolled_back_atomically(tmp_path):
    c=store()
    for i,data in enumerate([RESPONSE,{'unexpected':'bad'}]):
        c.execute('INSERT INTO checkout_idempotency VALUES(?,?,?,?,?)',(2,str(i),'payload',json.dumps(data),NOW.isoformat()))
    c.commit()
    with pytest.raises(CheckoutStorageError):
        with c:initialize(c,tmp_path/'db.sqlite3',now=NOW)
    assert all('format' not in json.loads(r[0]) for r in c.execute('SELECT response_json FROM checkout_idempotency'))


def test_concurrent_rotation_retains_every_new_key(tmp_path):
    path=tmp_path/'private.checkout-key';create_ring(path)
    with ThreadPoolExecutor(max_workers=4) as pool:ids=list(pool.map(lambda _:rotate_ring(path),range(4)))
    active,keys=read_ring(path)
    assert len(keys)==5 and all(k in keys for k in ids) and active in ids


def test_creation_and_rotation_sync_key_and_directory(tmp_path,monkeypatch):
    import stat
    observed=[];real=os.fsync
    def fsync(fd):
        observed.append('directory' if stat.S_ISDIR(os.fstat(fd).st_mode) else 'file')
        return real(fd)
    monkeypatch.setattr(os,'fsync',fsync)
    path=tmp_path/'durable.checkout-key';create_ring(path)
    assert observed==['file','directory']
    observed.clear();rotate_ring(path)
    assert observed==['file','directory']

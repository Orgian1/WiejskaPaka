"""Authenticated local storage for idempotent checkout replies, never a PIN log.

AES-256-GCM with random nonces; row identity and retention deadline are AAD.
The key ring is separate from the live database; never include it in source
archives or plaintext shared backups. Recovery containers require an independent
backup encryption key stored outside the archive directory.
"""
import base64
from datetime import datetime,timedelta,timezone
import hashlib
import json
import os
from pathlib import Path
import secrets
import stat
import tempfile
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

PIN_FIELDS=frozenset(('pin_test_only','shipment_pin_test_only'))
PIN_RETENTION=timedelta(hours=24)


class CheckoutStorageError(ValueError):
    pass


def canonical(data):return json.dumps(data,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')
def b64(data):return base64.b64encode(data).decode('ascii')
def unb64(data):return base64.b64decode(data,validate=True)


def read_ring(path):
    path=Path(path)
    if path.is_symlink():raise CheckoutStorageError('Plik klucza nie może być dowiązaniem')
    flags=os.O_RDONLY|getattr(os,'O_NOFOLLOW',0)|getattr(os,'O_NONBLOCK',0)
    fd=os.open(path,flags)
    try:
        info=os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or (os.name=='posix' and (info.st_uid!=os.getuid() or info.st_mode&0o077)):
            raise CheckoutStorageError('Niebezpieczne uprawnienia pliku klucza')
        with os.fdopen(fd,'rb',closefd=False) as stream:raw=stream.read(16385)
        if len(raw)>16384:raise ValueError('oversized key ring')
        ring=json.loads(raw)
        if set(ring)!= {'active','keys'} or type(ring['active']) is not str or not isinstance(ring['keys'],dict):raise ValueError('invalid key ring')
        keys={kid:unb64(value) for kid,value in ring['keys'].items()}
        if not keys or len(keys)>16 or ring['active'] not in keys:raise ValueError('invalid key ring')
        for kid,key in keys.items():
            if len(key)!=32 or kid!=hashlib.sha256(key).hexdigest()[:24]:raise ValueError('invalid key identity')
        return ring['active'],keys
    except (ValueError,TypeError,KeyError) as exc:
        raise CheckoutStorageError('Nieprawidłowy plik klucza') from exc
    finally:os.close(fd)


def sync_directory(path):
    if os.name!='posix':return
    fd=os.open(path,os.O_RDONLY|getattr(os,'O_DIRECTORY',0))
    try:os.fsync(fd)
    finally:os.close(fd)


def create_ring(path):
    """Atomic create-if-absent; a concurrent process can never see half a key."""
    path=Path(path)
    key=secrets.token_bytes(32);kid=hashlib.sha256(key).hexdigest()[:24]
    fd,temp=tempfile.mkstemp(prefix='.checkout-key-',dir=path.parent)
    try:
        with os.fdopen(fd,'wb') as stream:
            stream.write(canonical({'active':kid,'keys':{kid:b64(key)}}));stream.flush();os.fsync(stream.fileno())
        try:os.link(temp,path)
        except FileExistsError:pass
    finally:Path(temp).unlink(missing_ok=True)
    sync_directory(path.parent)
    return read_ring(path)


def deadline(value):
    value=datetime.fromisoformat(value)
    if value.tzinfo is None:raise ValueError('naive time')
    return value.astimezone(timezone.utc)


class Vault:
    def __init__(self,active,keys):self.active,self.keys=active,dict(keys)

    def seal(self,response,buyer_id,request_key,payload_hash,*,pin_until):
        header={'format':'wp-checkout-aesgcm-v1','key_id':self.active,'pin_until':pin_until,'pin_state':'sealed' if any(key in response for key in PIN_FIELDS) else 'redacted'}
        aad=canonical({'header':header,'buyer_id':buyer_id,'request_key':request_key,'payload_hash':payload_hash})
        nonce=secrets.token_bytes(12)
        ciphertext=AESGCM(self.keys[self.active]).encrypt(nonce,canonical(response),aad)
        return json.dumps({**header,'nonce':b64(nonce),'ciphertext':b64(ciphertext)},separators=(',',':'))

    def _decrypt(self,stored,buyer_id,request_key,payload_hash):
        try:
            envelope=json.loads(stored)
            if set(envelope)!= {'format','key_id','pin_until','pin_state','nonce','ciphertext'} or envelope['format']!='wp-checkout-aesgcm-v1' or envelope['pin_state'] not in ('sealed','redacted'):raise ValueError('invalid envelope')
            deadline(envelope['pin_until'])
            header={key:envelope[key] for key in ('format','key_id','pin_until','pin_state')}
            aad=canonical({'header':header,'buyer_id':buyer_id,'request_key':request_key,'payload_hash':payload_hash})
            nonce=unb64(envelope['nonce']);ct=unb64(envelope['ciphertext'])
            if len(nonce)!=12:raise ValueError('invalid nonce')
            response=json.loads(AESGCM(self.keys[envelope['key_id']]).decrypt(nonce,ct,aad))
            if type(response) is not dict or (envelope['pin_state']=='redacted' and any(key in response for key in PIN_FIELDS)):raise ValueError('invalid response')
            return response,envelope
        except (InvalidTag,ValueError,TypeError,KeyError,OverflowError) as exc:
            raise CheckoutStorageError('Nie można bezpiecznie odczytać wcześniejszego zakupu. Nie ponawiaj go z nowym kluczem.') from exc

    def open(self,stored,buyer_id,request_key,payload_hash,*,now=None,expose_pin=True):
        response,envelope=self._decrypt(stored,buyer_id,request_key,payload_hash)
        if not expose_pin or (now or datetime.now(timezone.utc))>=deadline(envelope['pin_until']):
            had_pin=any(key in response for key in PIN_FIELDS)
            response={key:value for key,value in response.items() if key not in PIN_FIELDS}
            if expose_pin and had_pin:response.update(pin_available=False,pin_notice=EXPIRED_NOTICE)
        return response


EXPIRED_NOTICE='Termin odzyskania PIN-u minął. Zakup już istnieje; nie składaj go ponownie.'


def redact(response):
    result={key:value for key,value in response.items() if key not in PIN_FIELDS}
    result.update(pin_available=False,pin_notice=EXPIRED_NOTICE)
    return result


def sweep(con,vault,*,now=None,postgres=False):
    now=now or datetime.now(timezone.utc);changed=0
    rows=con.execute('SELECT buyer_id,request_key,payload_hash,response_json FROM checkout_idempotency'+(' FOR UPDATE SKIP LOCKED' if postgres else '')).fetchall()
    for row in rows:
        envelope=json.loads(row['response_json'])
        if envelope['pin_state']=='redacted' or now<deadline(envelope['pin_until']):continue
        response,_=vault._decrypt(row['response_json'],row['buyer_id'],row['request_key'],row['payload_hash'])
        con.execute('UPDATE checkout_idempotency SET response_json=? WHERE buyer_id=? AND request_key=?',
                    (vault.seal(redact(response),row['buyer_id'],row['request_key'],row['payload_hash'],pin_until=envelope['pin_until']),row['buyer_id'],row['request_key']))
        changed+=1
    return changed


def initialize(con,database_path,*,postgres=False,key_path=None,now=None):
    """Seal legacy replies and redact expired PINs atomically; no new orders."""
    now=now or datetime.now(timezone.utc)
    rows=con.execute('SELECT buyer_id,request_key,payload_hash,response_json,created_at FROM checkout_idempotency'+(' FOR UPDATE' if postgres else '')).fetchall()
    path=Path(key_path) if key_path else Path(str(database_path)+'.checkout-key')
    if postgres and not key_path:raise CheckoutStorageError('PostgreSQL wymaga osobnego WP_CHECKOUT_KEY_FILE')
    if path.exists() or path.is_symlink():active,keys=read_ring(path)
    else:
        if key_path or any('wp-checkout-aesgcm-v1' in r['response_json'] for r in rows):
            raise CheckoutStorageError('Brak klucza istniejących zakupów; nie utworzono zastępczego klucza')
        active,keys=create_ring(path)
    vault=Vault(active,keys);changed=0
    for row in rows:
        raw=json.loads(row['response_json'])
        if raw.get('format')=='wp-checkout-aesgcm-v1':
            decoded,_=vault._decrypt(row['response_json'],row['buyer_id'],row['request_key'],row['payload_hash'])
            until=raw['pin_until']
            needs_redaction=now>=deadline(until) and any(key in decoded for key in PIN_FIELDS)
            if not needs_redaction:continue
            decoded=redact(decoded)
        else:
            if not isinstance(raw,dict) or not ('id' in raw or 'shipment_id' in raw):raise CheckoutStorageError('Nieprawidłowy starszy zapis zakupu')
            until=(deadline(row['created_at'])+PIN_RETENTION).isoformat();decoded=raw
            if now>=deadline(until):
                decoded=redact(decoded)
        con.execute('UPDATE checkout_idempotency SET response_json=? WHERE buyer_id=? AND request_key=?',
                    (vault.seal(decoded,row['buyer_id'],row['request_key'],row['payload_hash'],pin_until=until),row['buyer_id'],row['request_key']))
        changed+=1
    return vault,changed


def _rotate_ring_locked(path):
    """Retain old keys; operators restart the app after an atomic rotation."""
    path=Path(path);active,keys=read_ring(path)
    if len(keys)>=16:raise CheckoutStorageError('Limit kluczy; wymagany osobny plan migracji i kopii zapasowych')
    key=secrets.token_bytes(32);kid=hashlib.sha256(key).hexdigest()[:24];keys[kid]=key
    fd,temp=tempfile.mkstemp(prefix='.checkout-key-',dir=path.parent)
    try:
        with os.fdopen(fd,'wb') as stream:
            stream.write(canonical({'active':kid,'keys':{k:b64(v) for k,v in keys.items()}}));stream.flush();os.fsync(stream.fileno())
        os.replace(temp,path)
    finally:Path(temp).unlink(missing_ok=True)
    sync_directory(path.parent)
    return kid


def rotate_ring(path):
    # A separate stable lock inode survives replacing the key-ring file.
    if os.name!='posix':raise CheckoutStorageError('Rotacja wymaga lokalnego systemu POSIX; nie zmieniono klucza')
    import fcntl
    path=Path(path);lock=Path(str(path)+'.lock')
    fd=os.open(lock,os.O_CREAT|os.O_RDWR|getattr(os,'O_NOFOLLOW',0),0o600)
    try:
        info=os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_uid!=os.getuid() or info.st_mode&0o077:
            raise CheckoutStorageError('Niebezpieczne uprawnienia blokady klucza')
        fcntl.flock(fd,fcntl.LOCK_EX)
        return _rotate_ring_locked(path)
    finally:os.close(fd)

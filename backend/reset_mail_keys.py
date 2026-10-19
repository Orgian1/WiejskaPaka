"""Explicit, disabled-by-default key loading for the disconnected mail queue.

No key generation, file writes, environment hooks at import, or network access.
Actual app/worker integration is a separate step.
"""
import base64
import json
import os
from pathlib import Path
import stat

from backend.reset_mail_queue import KeyRing

ROOT=Path(__file__).resolve().parents[1]
MAX_BYTES=16384


def _unique(pairs):
    result={}
    for key,value in pairs:
        if key in result:raise ValueError('duplicate JSON member')
        result[key]=value
    return result


def load_keys(path, *, root=ROOT):
    """Read a private external POSIX file. Every failure is secret-free."""
    try:
        path=Path(path)
        if (os.name!='posix' or not path.is_absolute() or path.is_symlink()
                or path.resolve().is_relative_to(Path(root).resolve())):
            raise ValueError('private external POSIX file required')
        fd=os.open(path,os.O_RDONLY|getattr(os,'O_NOFOLLOW',0)|getattr(os,'O_NONBLOCK',0))
        try:
            info=os.fstat(fd)
            if (not stat.S_ISREG(info.st_mode) or info.st_uid!=os.getuid()
                    or info.st_mode&0o077 or info.st_size>MAX_BYTES):
                raise ValueError('unsafe key file')
            raw=os.read(fd,MAX_BYTES+1)
        finally:
            os.close(fd)
        if len(raw)>MAX_BYTES:raise ValueError('oversized key file')
        obj=json.loads(raw.decode('utf-8'),object_pairs_hook=_unique)
        if (not isinstance(obj,dict) or set(obj)!={'format','active','keys'}
                or type(obj['format']) is not int or obj['format']!=1
                or not isinstance(obj['active'],str) or not isinstance(obj['keys'],dict)
                or not 1<=len(obj['keys'])<=8):
            raise ValueError('invalid key format')
        keys={}
        for key,value in obj['keys'].items():
            if not isinstance(value,str):raise ValueError('invalid key encoding')
            decoded=base64.b64decode(value,validate=True)
            if len(decoded)!=32 or base64.b64encode(decoded).decode('ascii')!=value:
                raise ValueError('noncanonical 256-bit key')
            keys[key]=decoded
        if len(set(keys.values()))!=len(keys):raise ValueError('duplicate key material')
        return KeyRing(keys,obj['active'])
    except Exception:
        raise ValueError('MAIL_QUEUE_KEYS_REJECTED') from None


def load_config(environ=None, *, root=ROOT):
    """An opt-in permits a read only; it does not start a worker or SMTP."""
    env=dict(os.environ if environ is None else environ)
    if env.get('WP_ENABLE_MAIL_QUEUE')!='1':return None
    try:
        return load_keys(env['WP_MAIL_QUEUE_KEYS_FILE'],root=root)
    except Exception:
        raise ValueError('MAIL_QUEUE_KEYS_REJECTED') from None

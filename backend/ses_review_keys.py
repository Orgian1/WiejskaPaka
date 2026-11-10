"""Read-only, disabled-by-default independent keys for the SES REVIEW archive.

No keys are generated or persisted, no environment is read at import and no
listener/worker/database/network is started. Purpose binding rejects queue-key
files accidentally supplied as archive keys. Key provenance remains operator-owned.
"""
import base64
import os
from pathlib import Path
import stat
from backend.ses_feedback_archive import ArchiveCipher
from backend.sns_pinned_notification import json_object

ROOT=Path(__file__).resolve().parents[1]
MAX_BYTES=16384
PURPOSE='ses-feedback-review-v1'


def decode(raw):
    try:
        obj=json_object(raw,maximum=MAX_BYTES)
        if (set(obj)!={'format','purpose','active','keys'} or type(obj['format']) is not int or
                obj['format']!=1 or obj['purpose']!=PURPOSE or not isinstance(obj['active'],str) or
                not isinstance(obj['keys'],dict) or not 1<=len(obj['keys'])<=8):
            raise ValueError('Invalid document')
        keys={}
        for key,value in obj['keys'].items():
            if not isinstance(value,str):raise ValueError('Invalid encoding')
            material=base64.b64decode(value,validate=True)
            if len(material)!=32 or base64.b64encode(material).decode('ascii')!=value:
                raise ValueError('Invalid material')
            keys[key]=material
        if len(set(keys.values()))!=len(keys):raise ValueError('Duplicate material')
        return ArchiveCipher(keys,obj['active'])
    except Exception:raise ValueError('SES_REVIEW_KEYS_REJECTED') from None


def load_file(path,*,root=ROOT):
    """Existing external POSIX regular file, current owner, no group/other access."""
    try:
        path=Path(path)
        if (os.name!='posix' or not path.is_absolute() or path.is_symlink() or
                path.resolve().is_relative_to(Path(root).resolve())):
            raise ValueError('Protected external file required')
        fd=os.open(path,os.O_RDONLY|getattr(os,'O_NOFOLLOW',0)|getattr(os,'O_NONBLOCK',0))
        try:
            info=os.fstat(fd)
            if (not stat.S_ISREG(info.st_mode) or info.st_uid!=os.getuid() or
                    info.st_mode&0o077 or info.st_size>MAX_BYTES):
                raise ValueError('Unsafe file')
            raw=os.read(fd,MAX_BYTES+1)
        finally:os.close(fd)
        return decode(raw)
    except Exception:raise ValueError('SES_REVIEW_KEYS_REJECTED') from None


def load_config(environ=None,*,root=ROOT):
    env=dict(os.environ if environ is None else environ)
    if env.get('WP_ENABLE_SES_REVIEW_KEYS')!='1':return None
    try:return load_file(env['WP_SES_REVIEW_KEYS_FILE'],root=root)
    except Exception:raise ValueError('SES_REVIEW_KEYS_REJECTED') from None

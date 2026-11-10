"""Read-only operator-approved SNS pins, disabled by default.

The configuration file is an integrity/trust boundary, never a request field.
No certificate downloads, CA trust provisioning, file writes or API listeners.
Rotation is a new immutable snapshot loaded from an atomic file replacement.
"""
from dataclasses import dataclass,field
from datetime import datetime,timezone
import os
from pathlib import Path
import stat
import time
from cryptography import x509
from backend import ses_feedback
from backend.sns_pinned_notification import Pin,json_object
from backend.order_mail_outbox import _require_transaction

ROOT=Path(__file__).resolve().parents[1]
MAX_CONFIG=98304


@dataclass(frozen=True)
class FeedbackConfig:
    topic_arn:str
    source_arn:str
    pins:tuple=field(repr=False)


def decode(raw,*,now):
    """Validate bounded strict configuration, not arbitrary inbound event JSON."""
    try:
        if type(now) is not int or now<0:raise ValueError('Invalid clock')
        current=datetime.fromtimestamp(now,timezone.utc)
        obj=json_object(raw,maximum=MAX_CONFIG)
        if (set(obj)!={'format','topic_arn','source_arn','max_age_seconds','pins'} or
                type(obj['format']) is not int or obj['format']!=1 or
                not isinstance(obj['pins'],list) or not 1<=len(obj['pins'])<=4):
            raise ValueError('Invalid config document')
        ses_feedback.validate_source(obj['topic_arn'],obj['source_arn'])
        pins=[];urls=set();certificates=set();valid=0
        for item in obj['pins']:
            if (not isinstance(item,dict) or set(item)!={'certificate_url','certificate_pem'} or
                    not isinstance(item['certificate_pem'],str)):
                raise ValueError('Invalid certificate document')
            pem=item['certificate_pem'].encode('ascii')
            pin=Pin(obj['topic_arn'],item['certificate_url'],pem,obj['max_age_seconds'])
            if pin.certificate_url in urls or pem in certificates:raise ValueError('Duplicate pin')
            urls.add(pin.certificate_url);certificates.add(pem);pins.append(pin)
            cert=x509.load_pem_x509_certificate(pem)
            valid+=int(cert.not_valid_before_utc<=current<=cert.not_valid_after_utc)
        if not valid:raise ValueError('No currently valid certificate')
        return FeedbackConfig(obj['topic_arn'],obj['source_arn'],tuple(pins))
    except Exception:raise ValueError('SES_FEEDBACK_CONFIGURATION_REJECTED') from None


def load_file(path,*,root=ROOT,now=None):
    """Only existing external regular POSIX files, current owner, mode 0600/0400."""
    try:
        path=Path(path)
        if (os.name!='posix' or not path.is_absolute() or path.is_symlink() or
                path.resolve().is_relative_to(Path(root).resolve())):
            raise ValueError('Protected external POSIX file required')
        fd=os.open(path,os.O_RDONLY|getattr(os,'O_NOFOLLOW',0)|getattr(os,'O_NONBLOCK',0))
        try:
            info=os.fstat(fd)
            if (not stat.S_ISREG(info.st_mode) or info.st_uid!=os.getuid() or
                    info.st_mode&0o077 or info.st_size>MAX_CONFIG):
                raise ValueError('Unsafe configuration file')
            raw=os.read(fd,MAX_CONFIG+1)
        finally:os.close(fd)
        return decode(raw,now=int(time.time()) if now is None else now)
    except Exception:raise ValueError('SES_FEEDBACK_CONFIGURATION_REJECTED') from None


def load_config(environ=None,*,root=ROOT,now=None):
    env=dict(os.environ if environ is None else environ)
    if env.get('WP_ENABLE_SES_FEEDBACK_CONFIG')!='1':return None
    try:return load_file(env['WP_SES_FEEDBACK_CONFIG_FILE'],root=root,now=now)
    except Exception:raise ValueError('SES_FEEDBACK_CONFIGURATION_REJECTED') from None


def apply(con,raw,config,*,now):
    """Select only a pinned URL, then reverify raw bytes before any DB mutation."""
    _require_transaction(con)
    try:
        if not isinstance(config,FeedbackConfig):raise ValueError('Trusted configuration required')
        obj=json_object(raw)
        if obj.get('TopicArn')!=config.topic_arn:raise ValueError('Untrusted topic')
        matching=[pin for pin in config.pins if pin.certificate_url==obj.get('SigningCertURL')]
        if len(matching)!=1:raise ValueError('Unapproved certificate')
    except Exception:raise ValueError('SES_FEEDBACK_INPUT_REJECTED') from None
    return ses_feedback.apply(con,raw,matching[0],source_arn=config.source_arn,now=now)

"""Opt-in SMTP reset transport. Not connected to HTTP routes or a worker.

No connection occurs at import/configuration time. Callers must authorize the
recipient and persist delivery state before invoking this low-level adapter.
"""
from dataclasses import dataclass, field
from email.message import EmailMessage
from email.utils import formatdate, make_msgid
import os
from pathlib import Path
import re
import smtplib
import ssl
import stat
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class SMTPConfig:
    host: str
    port: int
    mode: str
    username: str = field(repr=False)
    password: str = field(repr=False)
    sender: str
    origin: str
    timeout: int = 10


def address(value):
    # Conservative ASCII mailboxes; no display names, lists or header controls.
    if not isinstance(value,str) or len(value)>254 or value.count('@')!=1:
        raise ValueError('Invalid mailbox')
    local, domain = value.split('@')
    if (not re.fullmatch(r"[A-Za-z0-9!#$%&'*+/=?^_`{|}~-]+(?:\.[A-Za-z0-9!#$%&'*+/=?^_`{|}~-]+)*",local)
            or len(local)>64 or not hostname(domain)):
        raise ValueError('Invalid mailbox')
    return value


def hostname(value):
    return (isinstance(value,str) and len(value)<=253 and '.' in value
            and all(re.fullmatch(r'[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?',label)
                    for label in value.split('.')))


def origin(value):
    parsed = urlsplit(value)
    if (parsed.scheme!='https' or not hostname(parsed.hostname) or parsed.username is not None
            or parsed.password is not None or parsed.query or parsed.fragment or parsed.path not in ('','/')
            or (parsed.port is not None and parsed.port!=443)):
        raise ValueError('Fixed HTTPS origin required')
    return 'https://' + parsed.hostname.lower()


def private_password(path, *, root=ROOT):
    path=Path(path)
    if not path.is_absolute() or path.resolve().is_relative_to(root.resolve()) or path.is_symlink():
        raise ValueError('Private external password file required')
    if os.name!='posix':
        raise ValueError('Password permissions require POSIX')
    fd=os.open(path,os.O_RDONLY|getattr(os,'O_NOFOLLOW',0)|getattr(os,'O_NONBLOCK',0))
    with os.fdopen(fd,'rb') as stream:
        info=os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_uid!=os.getuid() or info.st_mode&0o077 or info.st_size>4096:
            raise ValueError('Unsafe password file')
        raw=stream.read(4097)
    if len(raw)>4096:raise ValueError('Oversized password')
    password=raw.decode('utf-8').removesuffix('\n').removesuffix('\r')
    if not password or not password.isascii() or any(ord(c)<32 or ord(c)==127 for c in password):
        raise ValueError('Invalid password')
    return password


def load_config(environ=None, *, root=ROOT):
    """Disabled by default; invalid enabled settings raise a secret-free error."""
    env=dict(os.environ if environ is None else environ)
    if env.get('WP_ENABLE_SMTP')!='1':return None
    try:
        host=env['WP_SMTP_HOST'];mode=env['WP_SMTP_MODE']
        port=int(env['WP_SMTP_PORT']);timeout=int(env.get('WP_SMTP_TIMEOUT','10'))
        if not hostname(host) or (mode,port) not in (('implicit_tls',465),('starttls',587)) or not 1<=timeout<=30:
            raise ValueError('Invalid TLS settings')
        username=env['WP_SMTP_USERNAME']
        if not username or not username.isascii() or len(username)>254 or any(ord(c)<32 or ord(c)==127 for c in username):
            raise ValueError('Invalid username')
        sender=address(env['WP_SMTP_FROM']);base=origin(env['WP_PUBLIC_ORIGIN'])
        password=private_password(env['WP_SMTP_PASSWORD_FILE'],root=root)
        return SMTPConfig(host,port,mode,username,password,sender,base,timeout)
    except Exception:
        raise ValueError('SMTP_CONFIGURATION_REJECTED') from None


def reset_message(config, recipient, token):
    recipient=address(recipient)
    if not re.fullmatch(r'[A-Za-z0-9_-]{43}',token):raise ValueError('Invalid reset token')
    message=EmailMessage()
    message['From']=address(config.sender)
    message['To']=recipient
    message['Subject']='WiejskaPaka — zmiana hasła'
    message['Date']=formatdate(localtime=False,usegmt=True)
    message['Message-ID']=make_msgid(domain=config.sender.split('@')[1])
    link=origin(config.origin)+'/#reset-token='+token
    message.set_content('Otrzymaliśmy prośbę o zmianę hasła w WiejskiejPace.\n\n'
                        'Link jest ważny przez 15 minut i można go użyć jeden raz:\n'+link+
                        '\n\nJeśli nie prosisz o zmianę hasła, zignoruj tę wiadomość.\n'
                        'Nie odpowiadaj hasłem ani kodem odbioru paczki.\n')
    return message


def outcome(status, *, accepted=False, retryable=False):
    return {'status':status,'accepted_by_server':accepted,
            'delivery_confirmed':False,'retryable':retryable}


def send_reset(config, recipient, token, *, factory=None):
    """One attempt. Returns only fixed codes; never logs credentials or content.

    Acceptance by SMTP does not prove inbox delivery. An uncertain DATA result
    must not be blindly retried. A QUIT failure cannot undo prior acceptance.
    """
    if config is None:return outcome('DISABLED')
    try:
        message=reset_message(config,recipient,token)
        if (config.mode,config.port) not in (('implicit_tls',465),('starttls',587)):
            raise ValueError('TLS required')
        context=ssl.create_default_context()
        context.minimum_version=ssl.TLSVersion.TLSv1_2
    except (ValueError,TypeError,AttributeError):return outcome('MESSAGE_REJECTED')
    stage='connect';result=None
    try:
        implicit=config.mode=='implicit_tls'
        connect=factory or (smtplib.SMTP_SSL if implicit else smtplib.SMTP)
        options={'host':config.host,'port':config.port,'timeout':config.timeout,
                 'local_hostname':config.sender.split('@')[1]}
        if implicit:options['context']=context
        with connect(**options) as client:
            code,reply=client.ehlo()
            if code!=250:raise smtplib.SMTPHeloError(code,reply)
            if not implicit:
                client.starttls(context=context)
                code,reply=client.ehlo()
                if code!=250:raise smtplib.SMTPHeloError(code,reply)
            client.login(config.username,config.password)
            stage='data'
            refused=client.send_message(message,from_addr=config.sender,to_addrs=[recipient])
            if not isinstance(refused,dict):raise ValueError('Invalid submission result')
            if refused:
                result=outcome('REJECTED',retryable=all(400<=v[0]<500 for v in refused.values()))
            else:result=outcome('ACCEPTED',accepted=True)
        return result
    except (OSError,ValueError) as error:
        if result is not None:return result
        if isinstance(error,ssl.SSLError):return outcome('TLS_FAILED')
        if isinstance(error,smtplib.SMTPRecipientsRefused):
            return outcome('REJECTED',retryable=all(400<=v[0]<500 for v in error.recipients.values()))
        if isinstance(error,smtplib.SMTPResponseException):
            return outcome('REJECTED',retryable=400<=error.smtp_code<500)
        if stage=='data':return outcome('DELIVERY_UNCERTAIN')
        return outcome('CONNECTION_FAILED',retryable=not isinstance(error,smtplib.SMTPNotSupportedError))

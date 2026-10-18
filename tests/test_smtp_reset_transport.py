"""No real messages: all SMTP connections are replaced with an in-memory peer."""
from dataclasses import replace
import os
import smtplib
import ssl
import pytest
from backend import smtp_reset_transport as mail

TOKEN='t'*43


@pytest.fixture
def config():
    return mail.SMTPConfig('smtp.example.invalid',587,'starttls','private-user','private-password',
                           'noreply@example.invalid','https://app.example.invalid')


class Peer:
    def __init__(self, failure=None, quit_failure=False):
        self.events=[];self.failure=failure;self.quit_failure=quit_failure
    def __call__(self,**kwargs):self.options=kwargs;self.events.append('connect');return self
    def __enter__(self):return self
    def __exit__(self,*_):
        self.events.append('quit')
        if self.quit_failure:raise smtplib.SMTPServerDisconnected('private transcript')
    def ehlo(self):self.events.append('ehlo');return 250,b'ok'
    def starttls(self,**kwargs):
        self.events.append('starttls');self.context=kwargs['context']
        if self.failure=='tls':raise ssl.SSLCertVerificationError('private transcript')
    def login(self,*args):
        self.events.append('login')
        if self.failure=='auth':raise smtplib.SMTPAuthenticationError(535,b'private transcript')
    def send_message(self,message,**kwargs):
        self.events.append('send');self.message=message;self.envelope=kwargs
        if self.failure=='uncertain':raise smtplib.SMTPServerDisconnected('private transcript '+TOKEN)
        if self.failure=='temporary':raise smtplib.SMTPDataError(451,b'private transcript')
        if self.failure=='permanent':raise smtplib.SMTPRecipientsRefused({'buyer@example.invalid':(550,b'private transcript')})
        return {}


def test_disabled_transport_never_connects_or_reads_configuration(monkeypatch):
    def forbidden(*a,**kw):pytest.fail('No connection or credential read while disabled')
    monkeypatch.setattr(mail,'private_password',forbidden)
    assert mail.load_config({'WP_SMTP_PASSWORD_FILE':'private'}) is None
    assert mail.send_reset(None,'invalid','invalid',factory=forbidden)['status']=='DISABLED'


@pytest.mark.parametrize('mode,port',[('starttls',587),('implicit_tls',465)])
def test_tls_precedes_auth_and_one_recipient(config,mode,port):
    peer=Peer();cfg=replace(config,mode=mode,port=port)
    result=mail.send_reset(cfg,'buyer@example.invalid',TOKEN,factory=peer)
    assert result==mail.outcome('ACCEPTED',accepted=True)
    assert peer.events==(['connect','ehlo','starttls','ehlo','login','send','quit'] if mode=='starttls'
                         else ['connect','ehlo','login','send','quit'])
    context=peer.context if mode=='starttls' else peer.options['context']
    assert context.check_hostname and context.verify_mode==ssl.CERT_REQUIRED
    assert context.minimum_version>=ssl.TLSVersion.TLSv1_2
    assert peer.envelope=={'from_addr':cfg.sender,'to_addrs':['buyer@example.invalid']}
    assert TOKEN not in ''.join(str(v) for _,v in peer.message.items())
    assert 'https://app.example.invalid/#reset-token='+TOKEN in peer.message.get_content()
    assert 'private-password' not in repr(cfg)


@pytest.mark.parametrize('failure,status,retryable',[
    ('tls','TLS_FAILED',False),('auth','REJECTED',False),('uncertain','DELIVERY_UNCERTAIN',False),
    ('temporary','REJECTED',True),('permanent','REJECTED',False)])
def test_safe_failure_codes_and_uncertain_delivery(config,failure,status,retryable,capsys):
    peer=Peer(failure)
    result=mail.send_reset(config,'buyer@example.invalid',TOKEN,factory=peer)
    assert result==mail.outcome(status,retryable=retryable)
    if failure=='tls':assert 'login' not in peer.events and 'send' not in peer.events
    if failure=='auth':assert 'send' not in peer.events
    output=capsys.readouterr();assert not output.out and not output.err
    assert 'private' not in repr(result) and TOKEN not in repr(result)


def test_quit_error_does_not_trigger_duplicate_after_acceptance(config):
    peer=Peer(quit_failure=True)
    assert mail.send_reset(config,'buyer@example.invalid',TOKEN,factory=peer)['accepted_by_server']
    assert peer.events.count('send')==1


@pytest.mark.parametrize('recipient,token',[
    ('victim@example.invalid\r\nBcc:other@example.invalid',TOKEN),
    ('one@example.invalid,two@example.invalid',TOKEN),('Name <one@example.invalid>',TOKEN),
    ('one@example.invalid','bad-token'),('one@example.invalid',TOKEN+'\nBcc:private'),
])
def test_header_and_token_injection_rejected_before_connect(config,recipient,token):
    peer=Peer();result=mail.send_reset(config,recipient,token,factory=peer)
    assert result['status']=='MESSAGE_REJECTED' and not peer.events


@pytest.mark.parametrize('base',['http://app.example.invalid','https://user:private@app.example.invalid',
    'https://app.example.invalid/?next=private','https://app.example.invalid/#private',
    'https://app.example.invalid/other','https://app.example.invalid:8443'])
def test_link_origin_is_fixed_https_root(config,base):
    peer=Peer()
    assert mail.send_reset(replace(config,origin=base),'buyer@example.invalid',TOKEN,factory=peer)['status']=='MESSAGE_REJECTED'
    assert not peer.events


@pytest.mark.skipif(os.name!='posix',reason='Native secret file permissions require POSIX')
@pytest.mark.parametrize('kind',['valid','public','symlink','oversize','inside-project'])
def test_configuration_reads_only_private_external_password_file(tmp_path,kind):
    root=tmp_path/'project';root.mkdir()
    password=tmp_path/'smtp-secret';password.write_text('private-password\n');password.chmod(0o600)
    if kind=='public':password.chmod(0o644)
    elif kind=='symlink':
        link=tmp_path/'link';link.symlink_to(password);password=link
    elif kind=='oversize':password.write_bytes(b'x'*4097)
    elif kind=='inside-project':
        password=root/'secret';password.write_text('private-password');password.chmod(0o600)
    env={'WP_ENABLE_SMTP':'1','WP_SMTP_HOST':'smtp.example.invalid','WP_SMTP_MODE':'starttls',
         'WP_SMTP_PORT':'587','WP_SMTP_USERNAME':'user','WP_SMTP_FROM':'noreply@example.invalid',
         'WP_PUBLIC_ORIGIN':'https://app.example.invalid','WP_SMTP_PASSWORD_FILE':str(password)}
    if kind=='valid':assert mail.load_config(env,root=root).password=='private-password'
    else:
        with pytest.raises(ValueError,match='^SMTP_CONFIGURATION_REJECTED$'):mail.load_config(env,root=root)


@pytest.mark.parametrize('mode,port',[('plain',25),('starttls',25),('implicit_tls',587)])
def test_no_plaintext_or_mismatched_tls_mode(config,mode,port):
    peer=Peer()
    result=mail.send_reset(replace(config,mode=mode,port=port),'buyer@example.invalid',TOKEN,factory=peer)
    assert result['status']=='MESSAGE_REJECTED' and not peer.events


def test_missing_starttls_support_never_sends_credentials(config):
    class Unsupported(Peer):
        def starttls(self,**_):raise smtplib.SMTPNotSupportedError('private transcript')
    peer=Unsupported()
    result=mail.send_reset(config,'buyer@example.invalid',TOKEN,factory=peer)
    assert result['status']=='CONNECTION_FAILED' and not result['retryable']
    assert 'login' not in peer.events and 'send' not in peer.events


def test_explicit_refusal_survives_quit_disconnect(config):
    class Refused(Peer):
        def send_message(self,*a,**kw):return {'buyer@example.invalid':(450,b'private transcript')}
    peer=Refused(quit_failure=True)
    assert mail.send_reset(config,'buyer@example.invalid',TOKEN,factory=peer)==mail.outcome('REJECTED',retryable=True)

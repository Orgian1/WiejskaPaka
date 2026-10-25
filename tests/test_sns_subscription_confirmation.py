"""Synthetic signatures only: no AWS request is performed by these tests."""
import base64,json
from urllib.parse import urlencode
import pytest
from fastapi.testclient import TestClient
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from backend import sns_subscription_confirmation as confirmation
from backend.ses_feedback_config import FeedbackConfig
from backend.ses_feedback_http import create_app
from backend.ses_feedback_archive import ArchiveCipher
from tests.test_sns_pinned_notification import signer,NOW,TOPIC,CERT,envelope
from tests.test_ses_feedback import SOURCE


def signed(signer,**changes):
    obj=envelope(signer[0]);obj.pop('Signature')
    obj.update(Type='SubscriptionConfirmation',Token='synthetic-token',
        SubscribeURL='https://sns.eu-north-1.amazonaws.com/?'+urlencode({
            'Action':'ConfirmSubscription','TopicArn':TOPIC,'Token':'synthetic-token'}))
    obj.update(changes)
    fields=['Message','MessageId','SubscribeURL','Timestamp','Token','TopicArn','Type']
    canonical=''.join(k+'\n'+obj[k]+'\n' for k in fields).encode()
    obj['Signature']=base64.b64encode(signer[0].sign(canonical,padding.PKCS1v15(),hashes.SHA256())).decode()
    return json.dumps(obj)


def config(signer):return FeedbackConfig(TOPIC,SOURCE,(signer[1],))


def response(topic=TOPIC):
    return ('<ConfirmSubscriptionResponse xmlns="http://sns.amazonaws.com/doc/2010-03-31/">'
        '<ConfirmSubscriptionResult><SubscriptionArn>'+topic+':12345678-1234-1234-1234-123456789abc'
        '</SubscriptionArn></ConfirmSubscriptionResult></ConfirmSubscriptionResponse>').encode()


def test_signed_confirmation_uses_only_fixed_aws_endpoint(signer):
    calls=[]
    assert confirmation.confirm(signed(signer),config(signer),now=NOW,
        fetch=lambda url:(calls.append(url),response())[1])
    assert calls==['https://sns.eu-north-1.amazonaws.com/?'+urlencode({
        'Action':'ConfirmSubscription','TopicArn':TOPIC,'Token':'synthetic-token'})]


@pytest.mark.parametrize('change',[
    {'Type':'UnsubscribeConfirmation'}, {'SignatureVersion':'1'}, {'Token':''},
    {'Token':'x'*8193}, {'SigningCertURL':CERT.replace('synthetic','unknown')},
    {'TopicArn':TOPIC+'-other'}, {'Timestamp':'2020-01-01T00:00:00Z'},
    {'SubscribeURL':'https://169.254.169.254/'},
    {'SubscribeURL':'https://sns.eu-north-1.amazonaws.com.evil.invalid/'},
    {'SubscribeURL':'https://sns.eu-north-1.amazonaws.com@evil.invalid/'},
    {'SubscribeURL':'https://sns.eu-north-1.amazonaws.com/?Action=Unsubscribe'},
    {'SubscribeURL':'http://sns.eu-north-1.amazonaws.com/'},
])
def test_untrusted_confirmation_never_connects(signer,change):
    def forbidden(url):pytest.fail('Must verify before any outbound request')
    with pytest.raises(ValueError,match='^SNS_SUBSCRIPTION_CONFIRMATION_REJECTED$'):
        confirmation.confirm(signed(signer,**change),config(signer),now=NOW,fetch=forbidden)


def test_tampered_token_never_connects(signer):
    raw=signed(signer).replace('synthetic-token','changed-token')
    with pytest.raises(ValueError,match='CONFIRMATION_REJECTED'):
        confirmation.confirm(raw,config(signer),now=NOW,fetch=lambda url:pytest.fail('Tamper'))


@pytest.mark.parametrize('body',[b'<broken',b'x'*16385,response(TOPIC+'-other'),b'<html/>'])
def test_bad_aws_response_does_not_ack(signer,body):
    with pytest.raises(ValueError,match='CONFIRMATION_REJECTED'):
        confirmation.confirm(signed(signer),config(signer),now=NOW,fetch=lambda url:body)


def test_redirect_is_never_followed():
    with pytest.raises(ValueError,match='Redirect rejected'):
        confirmation.NoRedirect().redirect_request(None,None,302,'','', 'https://evil.invalid/')


def test_http_confirmation_is_opt_in_and_has_no_database_writes(signer):
    def forbidden():pytest.fail('Confirmation must not open database')
    cipher=ArchiveCipher({'test':b't'*32},'test')
    def confirm(raw,cfg,*,now):return confirmation.confirm(raw,cfg,now=now,fetch=lambda url:response())
    app=create_app(config(signer),cipher,forbidden,clock=lambda:NOW,confirmation=confirm)
    with TestClient(app) as client:
        assert client.post('/sns/feedback',content=signed(signer)).status_code==204
        assert client.post('/sns/feedback',content=signed(signer).replace('synthetic-token','tampered')).status_code==503
    calls=[]
    def unavailable():calls.append(True);raise ValueError('No database')
    disabled=create_app(config(signer),cipher,unavailable,clock=lambda:NOW)
    with TestClient(disabled) as client:
        assert client.post('/sns/feedback',content=signed(signer)).status_code==503
    assert calls==[True]


from tests.test_ses_feedback_service import prepared,environment


def test_service_requires_explicit_confirmation_flag(prepared,signer,monkeypatch):
    from backend import ses_feedback_service as service
    item,calls=prepared
    assert item.confirm_subscriptions is False
    enabled=service.prepare({**environment(),'WP_ENABLE_SES_SUBSCRIPTION_CONFIRMATION':'1'},now=NOW)
    assert enabled.confirm_subscriptions is True
    original=confirmation.confirm
    def confirm_without_network(raw,cfg,*,now):
        return original(raw,cfg,now=now,fetch=lambda url:response())
    monkeypatch.setattr(confirmation,'confirm',confirm_without_network)
    app=enabled.build_app(clock=lambda:NOW)
    assert len(calls)==1
    with TestClient(app) as client:
        assert client.post('/sns/feedback',content=signed(signer)).status_code==204
    assert len(calls)==1  # Startup probe only, no database work for confirmation.


def test_fetch_has_timeout_size_limit_and_no_proxy_or_redirect(monkeypatch):
    calls=[]
    class Response:
        status=200
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def read(self,size):calls.append(('read',size));return b'bounded'
    class Opener:
        def open(self,request,timeout):
            calls.append(('open',request.full_url,timeout,request.get_header('Accept-encoding')))
            return Response()
    def build(*handlers):
        assert handlers[0].proxies=={}
        assert isinstance(handlers[1],confirmation.NoRedirect)
        return Opener()
    monkeypatch.setattr(confirmation.urllib.request,'build_opener',build)
    assert confirmation.fetch_confirmation('https://sns.eu-north-1.amazonaws.com/')==b'bounded'
    assert calls==[('open','https://sns.eu-north-1.amazonaws.com/',5,'identity'),('read',16385)]

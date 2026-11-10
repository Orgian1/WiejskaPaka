"""Real RSA signatures with synthetic, explicitly pinned test certificates."""
import base64
from datetime import datetime,timedelta,timezone
import json
import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes,serialization
from cryptography.hazmat.primitives.asymmetric import rsa,padding
from cryptography.x509.oid import NameOID
from backend.sns_pinned_notification import Pin,verify

TOPIC='arn:aws:sns:eu-north-1:123456789012:ses-feedback'
CERT='https://sns.eu-north-1.amazonaws.com/SimpleNotificationService-synthetic.pem'
NOW=1792857600


def make_signer():
    key=rsa.generate_private_key(public_exponent=65537,key_size=2048)
    name=x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,'Synthetic pin; not an AWS trust claim')])
    now=datetime.fromtimestamp(NOW,timezone.utc)
    cert=(x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key())
        .serial_number(x509.random_serial_number()).not_valid_before(now-timedelta(days=8))
        .not_valid_after(now+timedelta(days=8)).sign(key,hashes.SHA256()))
    return key,Pin(TOPIC,CERT,cert.public_bytes(serialization.Encoding.PEM))


@pytest.fixture(scope='module')
def signer():return make_signer()

def envelope(key,message='synthetic\nzażółć',*,subject=None,**changes):
    obj={'Type':'Notification','MessageId':'12345678-1234-1234-1234-123456789abc',
         'Message':message,'Timestamp':datetime.fromtimestamp(NOW,timezone.utc).isoformat().replace('+00:00','Z'),
         'TopicArn':TOPIC,'SignatureVersion':'2','SigningCertURL':CERT}
    if subject is not None:obj['Subject']=subject
    obj.update(changes)
    fields=['Message','MessageId']+(['Subject'] if 'Subject' in obj else [])+['Timestamp','TopicArn','Type']
    canonical=''.join(k+'\n'+obj[k]+'\n' for k in fields).encode()
    obj['Signature']=base64.b64encode(key.sign(canonical,padding.PKCS1v15(),hashes.SHA256())).decode()
    return obj


@pytest.mark.parametrize('subject',[None,'Temat\nzażółć'])
def test_pinned_signature_and_optional_subject(signer,subject):
    key,pin=signer;raw=json.dumps(envelope(key,subject=subject))
    result=verify(raw,pin,now=NOW)
    assert result.message=='synthetic\nzażółć' and result.topic_arn==TOPIC
    assert 'synthetic' not in repr(result) and 'CERTIFICATE' not in repr(pin)


@pytest.mark.parametrize('field,value',[
    ('Message','modified-private-body'),('Signature','invalid'),('SignatureVersion','1'),
    ('TopicArn','arn:aws:sns:eu-north-1:123456789012:untrusted'),
    ('SigningCertURL','http://169.254.169.254/private'),('Type','SubscriptionConfirmation')])
def test_tamper_untrusted_topic_url_and_subscription_rejected(signer,field,value):
    key,pin=signer;obj=envelope(key);obj[field]=value
    with pytest.raises(ValueError,match='^SNS_NOTIFICATION_REJECTED$'):verify(json.dumps(obj),pin,now=NOW)


def test_different_signer_cannot_authenticate_against_pin(signer):
    _,pin=signer;other=rsa.generate_private_key(public_exponent=65537,key_size=2048)
    with pytest.raises(ValueError,match='NOTIFICATION_REJECTED'):verify(json.dumps(envelope(other)),pin,now=NOW)


@pytest.mark.parametrize('offset',[-61,86401,9*86400])
def test_freshness_future_and_expired_certificate_rejected(signer,offset):
    key,pin=signer
    with pytest.raises(ValueError,match='NOTIFICATION_REJECTED'):verify(json.dumps(envelope(key)),pin,now=NOW+offset)


@pytest.mark.parametrize('raw',['[]','{"Type":"one","Type":"two"}','{"value":NaN}','x'*131073],
                         ids=['array','duplicate-member','non-json-constant','oversize'])
def test_bounded_unambiguous_json_required(signer,raw):
    with pytest.raises(ValueError,match='NOTIFICATION_REJECTED'):verify(raw,signer[1],now=NOW)


def test_even_valid_signed_but_stale_or_non_utc_timestamp_rejected(signer):
    key,pin=signer
    for timestamp in ('2020-01-01T00:00:00Z','2026-10-24T16:00:00+00:00'):
        with pytest.raises(ValueError,match='NOTIFICATION_REJECTED'):
            verify(json.dumps(envelope(key,Timestamp=timestamp)),pin,now=NOW)


@pytest.mark.parametrize('offset',[-9*86400,9*86400])
def test_certificate_must_be_valid_even_when_notification_is_fresh(signer,offset):
    key,pin=signer;now=NOW+offset
    timestamp=datetime.fromtimestamp(now,timezone.utc).isoformat().replace('+00:00','Z')
    with pytest.raises(ValueError,match='NOTIFICATION_REJECTED'):
        verify(json.dumps(envelope(key,Timestamp=timestamp)),pin,now=now)


@pytest.mark.parametrize('url',['https://sns.eu-north-1.amazonaws.com.evil.invalid/SimpleNotificationService-x.pem',
    'https://sns.eu-north-1.amazonaws.com@evil.invalid/SimpleNotificationService-x.pem',
    'https://sns.eu-north-1.amazonaws.com/SimpleNotificationService-x.pem?redirect=private'])
def test_pin_rejects_confusable_or_redirecting_url(signer,url):
    with pytest.raises(ValueError,match='PIN_CONFIGURATION_REJECTED'):
        Pin(TOPIC,url,signer[1].certificate_pem)

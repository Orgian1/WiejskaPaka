"""Offline SNS SignatureVersion2 verification against an operator-approved pin.

The trusted certificate/topic configuration MUST NOT come from request fields.
No URL is downloaded. Pin provisioning and rotation are separate operations;
this module does not establish certificate trust from an arbitrary PEM itself.
"""
import base64
from dataclasses import dataclass,field
from datetime import datetime,timezone
import json
import re
from urllib.parse import urlsplit
from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding,rsa

MAX_BODY=131072
TOPIC=re.compile(r'arn:aws:sns:([a-z]{2}(?:-[a-z]+)+-[1-9]):([0-9]{12}):[A-Za-z0-9_-]{1,256}')
UUID=re.compile(r'[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}')


def _unique(pairs):
    obj={}
    for key,value in pairs:
        if key in obj:raise ValueError('Duplicate JSON member')
        obj[key]=value
    return obj


def _reject_constant(value):
    raise ValueError('Non-JSON constant rejected')


def json_object(raw,*,maximum=MAX_BODY):
    if not isinstance(raw,(str,bytes)) or len(raw)>maximum:raise ValueError('Bounded JSON required')
    if isinstance(raw,str):raw=raw.encode('utf-8')
    if len(raw)>maximum:raise ValueError('Bounded JSON required')
    obj=json.loads(raw,object_pairs_hook=_unique,parse_constant=_reject_constant)
    if not isinstance(obj,dict):raise ValueError('JSON object required')
    return obj


def _timestamp(value):
    if not isinstance(value,str) or not re.fullmatch(r'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d{1,6})?Z',value):
        raise ValueError('UTC timestamp required')
    return datetime.fromisoformat(value)


@dataclass(frozen=True)
class Pin:
    topic_arn:str
    certificate_url:str
    certificate_pem:bytes=field(repr=False)
    max_age_seconds:int=86400

    def __post_init__(self):
        try:
            topic=TOPIC.fullmatch(self.topic_arn)
            if not topic:raise ValueError('Invalid topic')
            parsed=urlsplit(self.certificate_url)
            if (parsed.scheme!='https' or parsed.netloc!='sns.'+topic[1]+'.amazonaws.com' or
                    parsed.query or parsed.fragment or
                    not re.fullmatch(r'/SimpleNotificationService-[A-Za-z0-9_-]{1,200}\.pem',parsed.path)):
                raise ValueError('Invalid certificate URL')
            if (not isinstance(self.certificate_pem,bytes) or len(self.certificate_pem)>16384 or
                    type(self.max_age_seconds) is not int or not 3600<=self.max_age_seconds<=604800):
                raise ValueError('Invalid pin')
            cert=x509.load_pem_x509_certificate(self.certificate_pem)
            key=cert.public_key()
            if not isinstance(key,rsa.RSAPublicKey) or not 2048<=key.key_size<=4096:
                raise ValueError('RSA key required')
        except Exception:raise ValueError('SNS_PIN_CONFIGURATION_REJECTED') from None


@dataclass(frozen=True)
class Notification:
    message_id:str
    topic_arn:str
    message:str=field(repr=False)


def verify(raw,pin,*,now):
    """Return Notification only after signature/topic/pin/freshness validation.

    Notification only is supported. Subscription URLs are never followed and
    certificates supplied by the untrusted message are never imported/fetched.
    """
    try:
        obj=_verify_envelope(raw,pin,now=now,kind='Notification')
        return Notification(obj['MessageId'].lower(),pin.topic_arn,obj['Message'])
    except Exception:raise ValueError('SNS_NOTIFICATION_REJECTED') from None


def _verify_envelope(raw,pin,*,now,kind):
    try:
        if not isinstance(pin,Pin) or type(now) is not int or now<0:raise ValueError('Invalid context')
        current=datetime.fromtimestamp(now,timezone.utc)
        obj=json_object(raw)
        required=('Type','MessageId','TopicArn','Message','Timestamp','SignatureVersion','Signature','SigningCertURL')
        if any(not isinstance(obj.get(k),str) for k in required):raise ValueError('Required strings')
        if (obj['Type']!=kind or obj['SignatureVersion']!='2' or
                obj['TopicArn']!=pin.topic_arn or obj['SigningCertURL']!=pin.certificate_url or
                not UUID.fullmatch(obj['MessageId']) or len(obj['Signature'])>1024 or
                ('Subject' in obj and (not isinstance(obj['Subject'],str) or len(obj['Subject'])>1024))):
            raise ValueError('Untrusted envelope')
        sent=_timestamp(obj['Timestamp'])
        age=(current-sent).total_seconds()
        if not -60<=age<=pin.max_age_seconds:raise ValueError('Expired notification')
        cert=x509.load_pem_x509_certificate(pin.certificate_pem)
        if not (cert.not_valid_before_utc<=sent<=cert.not_valid_after_utc and
                cert.not_valid_before_utc<=current<=cert.not_valid_after_utc):
            raise ValueError('Expired pin')
        fields=['Message','MessageId']+(['Subject'] if 'Subject' in obj else [])+['Timestamp','TopicArn','Type']
        if kind=='SubscriptionConfirmation':
            if (not isinstance(obj.get('Token'),str) or not 1<=len(obj['Token'])<=8192 or
                    not isinstance(obj.get('SubscribeURL'),str) or len(obj['SubscribeURL'])>16384 or
                    'Subject' in obj):raise ValueError('Invalid confirmation')
            fields=['Message','MessageId','SubscribeURL','Timestamp','Token','TopicArn','Type']
        canonical=''.join(k+'\n'+obj[k]+'\n' for k in fields).encode('utf-8')
        signature=base64.b64decode(obj['Signature'],validate=True)
        cert.public_key().verify(signature,canonical,padding.PKCS1v15(),hashes.SHA256())
        return obj
    except Exception:raise ValueError('SNS_NOTIFICATION_REJECTED') from None

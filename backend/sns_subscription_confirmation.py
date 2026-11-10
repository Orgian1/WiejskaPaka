"""Explicit opt-in confirmation of pinned SNS subscriptions, no URL following.

Verify before networking. Reconstruct only the regional AWS ConfirmSubscription
request; never fetch SubscribeURL, certificates or redirects from the envelope.
"""
import urllib.request
from urllib.parse import urlencode, urlsplit, parse_qs
import xml.etree.ElementTree as ET
from backend.sns_pinned_notification import _verify_envelope,json_object,TOPIC,UUID


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):
        raise ValueError('Redirect rejected')


def fetch_confirmation(url):
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect())
    request=urllib.request.Request(url,headers={'Accept-Encoding':'identity'})
    with opener.open(request,timeout=5) as response:
        if response.status!=200:raise ValueError('Confirmation failed')
        body=response.read(16385)
        if len(body)>16384:raise ValueError('Response too large')
        return body


def confirm(raw,config,*,now,fetch=fetch_confirmation):
    try:
        obj=json_object(raw)
        pins=[p for p in config.pins if p.certificate_url==obj.get('SigningCertURL')]
        if len(pins)!=1:raise ValueError('Unknown pin')
        obj=_verify_envelope(raw,pins[0],now=now,kind='SubscriptionConfirmation')
        if obj['TopicArn']!=config.topic_arn:raise ValueError('Wrong topic')
        region=TOPIC.fullmatch(config.topic_arn)[1]
        host='sns.'+region+'.amazonaws.com'
        signed_url=urlsplit(obj['SubscribeURL'])
        query=parse_qs(signed_url.query,strict_parsing=True,keep_blank_values=True)
        expected={'Action':['ConfirmSubscription'],'TopicArn':[config.topic_arn],'Token':[obj['Token']]}
        if (signed_url.scheme!='https' or signed_url.netloc!=host or
                signed_url.path not in ('','/') or signed_url.fragment or query!=expected):
            raise ValueError('Unexpected confirmation URL')
        # Use our own endpoint and canonical query, not the URL received by HTTP.
        url='https://'+host+'/?'+urlencode({key:values[0] for key,values in expected.items()})
        body=fetch(url)
        if not isinstance(body,bytes) or len(body)>16384:raise ValueError('Invalid response')
        document=ET.fromstring(body)
        ns='{http://sns.amazonaws.com/doc/2010-03-31/}'
        if document.tag!=ns+'ConfirmSubscriptionResponse':raise ValueError('Wrong response')
        arn=document.findtext(ns+'ConfirmSubscriptionResult/'+ns+'SubscriptionArn')
        prefix=config.topic_arn+':'
        if not isinstance(arn,str) or not arn.startswith(prefix) or not UUID.fullmatch(arn[len(prefix):]):
            raise ValueError('Wrong subscription')
        return True
    except Exception:raise ValueError('SNS_SUBSCRIPTION_CONFIRMATION_REJECTED') from None

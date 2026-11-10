from dataclasses import replace
from datetime import datetime, timedelta, timezone
import pytest
from backend import order_mail as mail
from backend import smtp_reset_transport as smtp
from tests.test_smtp_reset_transport import Peer, config


@pytest.fixture
def purchase():
    return mail.PurchaseMail('WPS-'+'A'*24,(('Pomidory',2,'kg',698),('Ogórki',1,'sloik',299)),
        501,1498,(datetime.now(timezone.utc)+timedelta(minutes=30)).isoformat(),'a'*64,'012345')


def test_polish_confirmation_uses_integer_money_one_delivery_and_private_pin(config,purchase):
    message=mail.purchase_message(config,'buyer@example.invalid',purchase,email_verified=True)
    body=message.get_content()
    assert '14,98 zł' in body and 'Dostawa za całą paczkę: 5,01 zł' in body
    assert body.count('PIN odbioru: 012345')==1 and '2 kg' in body
    assert 'Nie wykonano prawdziwej płatności' in body
    assert 'Sprawdź towar przed podaniem' in body
    assert message['To']=='buyer@example.invalid' and not message.get('Cc') and not message.get('Bcc')
    assert '012345' not in repr(purchase)
    assert message['Message-ID']==mail.purchase_message(config,'buyer@example.invalid',purchase,email_verified=True)['Message-ID']


@pytest.mark.parametrize('verified',[False,None,1,'true'])
def test_unverified_recipient_is_rejected_before_connection(config,purchase,verified):
    peer=Peer()
    result=mail.send_purchase(config,'buyer@example.invalid',purchase,email_verified=verified,factory=peer)
    assert result['status']=='MESSAGE_REJECTED' and not peer.events


@pytest.mark.parametrize('changes',[
    {'reference':'WP-x\r\nBcc:other@example.invalid'}, {'pin':'123'},
    {'total_grosze':1499},{'total_grosze':1498.0},{'delivery_grosze':True},
    {'lines':(('Bad',True,'kg',997),)}, {'lines':(('Bad',1,'unknown',997),)},
    {'expires_at':'2026-10-24T00:00:00'}, {'message_key':'private-key'},
])
def test_malformed_purchase_never_reaches_smtp(config,purchase,changes):
    peer=Peer();result=mail.send_purchase(config,'buyer@example.invalid',replace(purchase,**changes),
                                       email_verified=True,factory=peer)
    assert result['status']=='MESSAGE_REJECTED' and not peer.events


def test_purchase_smtp_tls_precedes_auth_and_never_retries_uncertain_data(config,purchase,capsys):
    peer=Peer(failure='uncertain')
    result=mail.send_purchase(config,'buyer@example.invalid',purchase,email_verified=True,factory=peer)
    assert peer.events==['connect','ehlo','starttls','ehlo','login','send','quit']
    assert peer.envelope['to_addrs']==['buyer@example.invalid']
    assert result==smtp.outcome('DELIVERY_UNCERTAIN')
    assert not ''.join(capsys.readouterr())


def test_extra_envelope_recipient_is_rejected(config,purchase):
    message=mail.purchase_message(config,'buyer@example.invalid',purchase,email_verified=True)
    message['Bcc']='other@example.invalid';peer=Peer()
    assert smtp.submit_message(config,'buyer@example.invalid',message,factory=peer)['status']=='MESSAGE_REJECTED'
    assert not peer.events


def test_disabled_ses_does_not_read_password_or_connect(monkeypatch):
    monkeypatch.setattr(smtp,'private_password',lambda *a,**k:pytest.fail('Must remain disabled'))
    assert mail.load_ses_config({}) is None
    assert mail.send_purchase(None,None,None)['status']=='DISABLED'


def test_ses_region_endpoint_and_sender_match_before_reading_secret(monkeypatch,config):
    env={'WP_ENABLE_ORDER_SMTP':'1','WP_SES_REGION':'eu-north-1','WP_SES_DOMAIN':'wiejskapaka.pl',
         'WP_SMTP_HOST':'email-smtp.eu-north-1.amazonaws.com','WP_SMTP_FROM':'noreply@wiejskapaka.pl'}
    def loader(source,**kwargs):
        assert source['WP_ENABLE_SMTP']=='1';return config
    monkeypatch.setattr(smtp,'load_config',loader)
    assert mail.load_ses_config(env) is config
    assert 'WP_ENABLE_SMTP' not in env
    for key,value in [('WP_SES_REGION','private-region'),('WP_SMTP_HOST','smtp.other.invalid'),
                      ('WP_SMTP_FROM','noreply@other.invalid')]:
        with pytest.raises(ValueError,match='^SES_ORDER_CONFIGURATION_REJECTED$'):
            mail.load_ses_config({**env,key:value})

import pytest
from backend import email_verification_mail as mail
from backend.smtp_reset_transport import outcome
from tests.test_smtp_reset_transport import Peer, config


def test_private_fragment_link_and_tls_transport(config):
    token='a'*43;peer=Peer()
    message=mail.message(config,'buyer@example.invalid',token)
    body=message.get_content()
    assert '/#verify-email='+token in body and '15 minut' in body
    assert token not in str(message.items())
    assert mail.send(config,'buyer@example.invalid',token,factory=peer)==outcome('ACCEPTED',accepted=True)
    assert peer.events==['connect','ehlo','starttls','ehlo','login','send','quit']


@pytest.mark.parametrize('token',['x','a'*42+'\n',None])
def test_bad_token_never_contacts_smtp(config,token):
    peer=Peer()
    assert mail.send(config,'buyer@example.invalid',token,factory=peer)['status']=='MESSAGE_REJECTED'
    assert not peer.events


def test_disabled_and_uncertain_not_delivery_claim(config):
    assert mail.send(None,'buyer@example.invalid','a'*43)==outcome('DISABLED')
    peer=Peer(failure='uncertain')
    assert mail.send(config,'buyer@example.invalid','a'*43,factory=peer)==outcome('DELIVERY_UNCERTAIN')

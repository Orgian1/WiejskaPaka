"""Verification link template using the shared TLS-only SMTP transport."""
import re
from email.message import EmailMessage
from email.utils import formatdate, make_msgid
from backend.smtp_reset_transport import address, origin, outcome, submit_message


def message(config,recipient,token):
    if not isinstance(token,str) or not re.fullmatch(r'[A-Za-z0-9_-]{43}',token):
        raise ValueError('EMAIL_VERIFICATION_TOKEN_REJECTED')
    mail=EmailMessage()
    mail['From']=address(config.sender)
    mail['To']=address(recipient)
    mail['Subject']='WiejskaPaka — potwierdź adres e-mail'
    mail['Date']=formatdate(localtime=False,usegmt=True)
    mail['Message-ID']=make_msgid(domain=config.sender.split('@')[1])
    link=origin(config.origin)+'/#verify-email='+token
    mail.set_content('Potwierdź adres e-mail swojego konta WiejskaPaka.\n\n'
        'Zaloguj się na konto, dla którego zamówiono link, i otwórz:\n'+link+
        '\n\nLink jest ważny 15 minut i można go użyć jeden raz.\n'
        'Jeżeli nie prosisz o potwierdzenie, zignoruj tę wiadomość.\n'
        'Nie podawaj nikomu swojego hasła ani PIN-u odbioru.\n')
    return mail


def send(config,recipient,token,*,factory=None):
    if config is None:return outcome('DISABLED')
    try:mail=message(config,recipient,token)
    except (ValueError,TypeError,AttributeError):return outcome('MESSAGE_REJECTED')
    return submit_message(config,recipient,mail,factory=factory)

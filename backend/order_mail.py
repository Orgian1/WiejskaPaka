"""Private preparation of test-purchase mail; no HTTP, environment or network hooks."""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from email.message import EmailMessage
from email.utils import formatdate
import hashlib
import os
import re

from backend.smtp_reset_transport import address, hostname, origin, outcome, submit_message

UNITS={'szt':'szt.','kg':'kg','g':'g','l':'l','ml':'ml','opak':'opak.',
       'peczek':'pęczek','sloik':'słoik','butelka':'butelka','worek':'worek',
       'skrzynka':'skrzynka','tacka':'tacka'}


@dataclass(frozen=True)
class PurchaseMail:
    reference: str
    lines: tuple = field(repr=False)
    delivery_grosze: int
    total_grosze: int
    expires_at: str
    message_key: str = field(repr=False)
    pin: str = field(repr=False)


def money(value):
    if type(value) is not int or not 0<=value<=9223372036854775807:
        raise ValueError('ORDER_MAIL_AMOUNT_REJECTED')
    return f'{value//100},{value%100:02d} zł'


def purchase_message(config,recipient,purchase,*,email_verified=False):
    """Trusted worker only: email_verified must come from confirmed account ownership."""
    if email_verified is not True:raise ValueError('ORDER_MAIL_UNVERIFIED_RECIPIENT')
    from backend.notification_policy import validate_channel, Event, Channel
    validate_channel(Event.ORDER_CONFIRMED,Channel.EMAIL,email_verified=email_verified)
    validate_channel(Event.PICKUP_PIN,Channel.EMAIL,email_verified=email_verified)
    recipient=address(recipient)
    if (not isinstance(purchase,PurchaseMail) or
            not re.fullmatch(r'(?:WP|WPS)-[A-F0-9]{10,24}',purchase.reference) or
            not re.fullmatch(r'[0-9]{6}',purchase.pin) or
            not re.fullmatch(r'[a-f0-9]{64}',purchase.message_key) or
            not isinstance(purchase.lines,tuple) or not 1<=len(purchase.lines)<=50):
        raise ValueError('ORDER_MAIL_PURCHASE_REJECTED')
    expiry=datetime.fromisoformat(purchase.expires_at)
    if expiry.tzinfo is None:raise ValueError('ORDER_MAIL_EXPIRY_REJECTED')
    rows=[];subtotal=0
    for line in purchase.lines:
        if not isinstance(line,tuple) or len(line)!=4:raise ValueError('ORDER_MAIL_LINE_REJECTED')
        name,quantity,unit,line_total=line
        if (not isinstance(name,str) or not 1<=len(name)<=180 or
                type(quantity) is not int or not 1<=quantity<=1000 or unit not in UNITS):
            raise ValueError('ORDER_MAIL_LINE_REJECTED')
        rows.append(f'- {" ".join(name.split())}: {quantity} {UNITS[unit]} — {money(line_total)}')
        subtotal+=line_total
    if subtotal+purchase.delivery_grosze!=purchase.total_grosze:
        raise ValueError('ORDER_MAIL_TOTAL_REJECTED')
    message=EmailMessage()
    message['From']=address(config.sender);message['To']=recipient
    message['Subject']='WiejskaPaka — rezerwacja testowa '+purchase.reference
    message['Date']=formatdate(localtime=False,usegmt=True)
    message['Message-ID']='<order-'+purchase.message_key+'@'+config.sender.split('@')[1]+'>'
    message.set_content('Potwierdzamy zapis rezerwacji testowej w WiejskiejPace.\n'
        'To środowisko testowe. Nie wykonano prawdziwej płatności.\n\n'
        'Numer zamówienia / paczki: '+purchase.reference+'\n\n'+'\n'.join(rows)+
        '\n\nProdukty: '+money(subtotal)+'\nDostawa za całą paczkę: '+money(purchase.delivery_grosze)+
        '\nRazem: '+money(purchase.total_grosze)+'\nTermin rezerwacji (UTC): '+
        expiry.astimezone(timezone.utc).isoformat()+'\n\nPIN odbioru: '+purchase.pin+
        '\nZachowaj PIN dla siebie. Sprawdź towar przed podaniem go przy odbiorze.\n'
        'Aktualny status i warunki dostawy sprawdzisz po zalogowaniu:\n'+
        origin(config.origin)+'/#orders-section\n\n'
        'Nie odpowiadaj hasłem ani PIN-em na wiadomości e-mail.\n')
    return message


def send_purchase(config,recipient,purchase,*,email_verified=False,factory=None):
    if config is None:return outcome('DISABLED')
    try:message=purchase_message(config,recipient,purchase,email_verified=email_verified)
    except (ValueError,TypeError,AttributeError,KeyError):return outcome('MESSAGE_REJECTED')
    return submit_message(config,recipient,message,factory=factory)


def load_ses_config(environ=None,*,root=None):
    """Explicit opt-in; reuse protected SMTP password loading, never AWS root keys."""
    env=dict(os.environ if environ is None else environ)
    if env.get('WP_ENABLE_ORDER_SMTP')!='1':return None
    try:
        region=env['WP_SES_REGION'];domain=env['WP_SES_DOMAIN']
        if (not re.fullmatch(r'[a-z]{2}(?:-[a-z]+)+-[1-9]',region) or not hostname(domain)
                or env['WP_SMTP_HOST']!='email-smtp.'+region+'.amazonaws.com'
                or address(env['WP_SMTP_FROM']).split('@')[1].lower()!=domain.lower()):
            raise ValueError('Invalid SES settings')
        from backend.smtp_reset_transport import load_config
        env['WP_ENABLE_SMTP']='1'
        return load_config(env,**({'root':root} if root is not None else {}))
    except Exception:raise ValueError('SES_ORDER_CONFIGURATION_REJECTED') from None


def checkout_purchase(con,vault,buyer_id,request_key,*,now):
    """Reconstruct only the buyer's immutable purchase; PIN stays in the existing vault."""
    from backend.pin_recovery import reply_order_ids
    from backend.purchase_records import order_record
    from backend.pg_adapter import PgConnection
    row=con.execute('SELECT * FROM checkout_idempotency WHERE buyer_id=? AND request_key=?',
                    (buyer_id,request_key)).fetchone()
    if row is None:raise ValueError('ORDER_MAIL_PURCHASE_UNAVAILABLE')
    reply=vault.open(row['response_json'],buyer_id,request_key,row['payload_hash'],now=now,expose_pin=True)
    pin=reply.get('shipment_pin_test_only',reply.get('pin_test_only'))
    if not isinstance(pin,str) or not re.fullmatch(r'[0-9]{6}',pin):
        raise ValueError('ORDER_MAIL_PIN_EXPIRED')
    if isinstance(con,PgConnection):
        units=con.execute("SELECT to_regclass('public.order_sale_units') AS name").fetchone()['name'] is not None
    else:
        units=con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='order_sale_units'").fetchone() is not None
    lines=[];delivery=0;total=0;expires=[];farmers=set()
    for oid in reply_order_ids(reply):
        order=con.execute('SELECT * FROM orders WHERE id=? AND buyer_id=?',(oid,buyer_id)).fetchone()
        if order is None or order['status']!='oczekuje_na_platnosc_testowa':
            raise ValueError('ORDER_MAIL_PURCHASE_UNAVAILABLE')
        original=order_record(con,order)['original']
        if original is None:raise ValueError('ORDER_MAIL_PURCHASE_UNAVAILABLE')
        unit_row=con.execute('SELECT unit FROM order_sale_units WHERE order_id=?',(oid,)).fetchone() if units else None
        unit=unit_row['unit'] if unit_row else 'szt'
        lines.append((original['product']['name'],original['quantity'],unit,original['subtotal_grosze']))
        delivery+=original['delivery_grosze'];total+=original['total_grosze']
        expires.append(datetime.fromisoformat(original['reservation_expires_at']))
        farmers.add(order['farmer_id'])
    if (len(farmers)!=1 or not expires or any(t.tzinfo is None or now>=t for t in expires)
            or reply.get('total_grosze')!=total):raise ValueError('ORDER_MAIL_PURCHASE_UNAVAILABLE')
    reference=reply.get('shipment_id',reply.get('pickup_code'))
    key=hashlib.sha256((str(buyer_id)+':'+request_key).encode()).hexdigest()
    return PurchaseMail(reference,tuple(lines),delivery,total,min(expires).isoformat(),key,pin)

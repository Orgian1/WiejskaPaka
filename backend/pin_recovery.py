"""Buyer-only recovery of an existing test PIN; never issue or reset a PIN."""
from datetime import datetime, timedelta, timezone
import re

from argon2.exceptions import VerificationError, InvalidHashError
from backend.checkout_vault import CheckoutStorageError
from backend.inventory_reservations import payment_deadline_passed
from backend.time_safety import utc_datetime

SCHEMA_SQLITE = '''
CREATE TABLE IF NOT EXISTS checkout_pin_links (
    order_id INTEGER PRIMARY KEY REFERENCES orders(id),
    buyer_id INTEGER NOT NULL,
    request_key TEXT NOT NULL,
    FOREIGN KEY(buyer_id,request_key) REFERENCES checkout_idempotency(buyer_id,request_key)
);
CREATE INDEX IF NOT EXISTS checkout_pin_links_request ON checkout_pin_links(buyer_id,request_key);
CREATE TABLE IF NOT EXISTS checkout_pin_access (
    buyer_id INTEGER PRIMARY KEY REFERENCES users(id),
    attempts INTEGER NOT NULL CHECK(attempts BETWEEN 1 AND 5),
    window_started_at TEXT NOT NULL
);
'''
WINDOW = timedelta(minutes=15)
MAX_ATTEMPTS = 5
UNAVAILABLE = 'PIN niedostępny dla tego zakupu. Nie składaj zamówienia ponownie.'


class RecoveryError(ValueError):
    def __init__(self, status, message, headers=None):
        super().__init__(message)
        self.status, self.headers = status, headers


def reply_order_ids(response):
    if 'shipment_id' in response:
        orders = response.get('orders')
        if not isinstance(orders,list) or not orders or any(type(o) is not dict for o in orders):
            raise CheckoutStorageError(UNAVAILABLE)
        ids = [o.get('id') for o in orders]
    else:
        ids = [response.get('id')]
    if any(type(oid) is not int or oid < 1 for oid in ids) or len(set(ids)) != len(ids):
        raise CheckoutStorageError(UNAVAILABLE)
    return ids


def link_reply(con, buyer_id, request_key, response):
    """Called in the checkout transaction, or for authenticated legacy backfill."""
    for oid in reply_order_ids(response):
        order = con.execute('SELECT buyer_id FROM orders WHERE id=?',(oid,)).fetchone()
        if not order or order['buyer_id'] != buyer_id:
            raise CheckoutStorageError(UNAVAILABLE)
        con.execute('''INSERT INTO checkout_pin_links(order_id,buyer_id,request_key)
            VALUES(?,?,?) ON CONFLICT(order_id) DO NOTHING''',(oid,buyer_id,request_key))
        link = con.execute('SELECT buyer_id,request_key FROM checkout_pin_links WHERE order_id=?',(oid,)).fetchone()
        if link['buyer_id'] != buyer_id or link['request_key'] != request_key:
            raise CheckoutStorageError(UNAVAILABLE)


def backfill_links(con, vault):
    """Keep old encrypted purchases recoverable without extending their deadline."""
    rows = con.execute('SELECT buyer_id,request_key,payload_hash,response_json FROM checkout_idempotency').fetchall()
    for row in rows:
        response = vault.open(row['response_json'],row['buyer_id'],row['request_key'],row['payload_hash'],expose_pin=False)
        link_reply(con,row['buyer_id'],row['request_key'],response)
    return len(rows)


def consume_attempt(con, buyer_id, now):
    """Caller serializes per buyer. Count successes and failures across sessions."""
    row = con.execute('SELECT attempts,window_started_at FROM checkout_pin_access WHERE buyer_id=?',(buyer_id,)).fetchone()
    start = utc_datetime(row['window_started_at']) if row else now
    if start > now:
        # A backward clock jump cannot reopen the window.
        raise RecoveryError(429,'Zbyt wiele prób odzyskania PIN-u. Spróbuj później.',{'Retry-After':'900'})
    active = now < start + WINDOW
    if row and active and row['attempts'] >= MAX_ATTEMPTS:
        remaining = start + WINDOW - now
        seconds = max(1,(remaining.days*86400+remaining.seconds)+(1 if remaining.microseconds else 0))
        raise RecoveryError(429,'Zbyt wiele prób odzyskania PIN-u. Spróbuj później.',{'Retry-After':str(seconds)})
    count = row['attempts'] + 1 if row and active else 1
    con.execute('''INSERT INTO checkout_pin_access(buyer_id,attempts,window_started_at)
        VALUES(?,?,?) ON CONFLICT(buyer_id) DO UPDATE SET
        attempts=excluded.attempts,window_started_at=excluded.window_started_at''',
        (buyer_id,count,(start if active else now).isoformat()))


def recover(con, vault, hasher, buyer_id, password, *, order_id=None, shipment_id=None, postgres=False, now=None):
    """Caller authenticates inside the transaction, locks buyer, commits denials."""
    # Match fulfillment's group-before-orders lock order, including order URLs
    # that refer to a position in a shipment.
    if shipment_id is None:
        order = con.execute('SELECT buyer_id FROM orders WHERE id=?',(order_id,)).fetchone()
        if not order or order['buyer_id'] != buyer_id:raise RecoveryError(404,'Brak zakupu')
        link = con.execute('SELECT shipment_id FROM shipment_order_links WHERE order_id=?',(order_id,)).fetchone()
        if link:shipment_id = link['shipment_id']
    if shipment_id is not None:
        group = con.execute('SELECT buyer_id FROM shipment_groups WHERE id=?'+(' FOR UPDATE' if postgres else ''),(shipment_id,)).fetchone()
        if not group or group['buyer_id'] != buyer_id:raise RecoveryError(404,'Brak zakupu')
        orders = con.execute('''SELECT o.* FROM orders o JOIN shipment_order_links l ON l.order_id=o.id
            WHERE l.shipment_id=? ORDER BY o.id'''+(' FOR UPDATE OF o' if postgres else ''),(shipment_id,)).fetchall()
    else:
        orders = con.execute('SELECT * FROM orders WHERE id=?'+(' FOR UPDATE' if postgres else ''),(order_id,)).fetchall()
    if not orders or any(o['buyer_id'] != buyer_id for o in orders):raise RecoveryError(404,'Brak zakupu')
    now = now or datetime.now(timezone.utc)
    consume_attempt(con,buyer_id,now)
    user = con.execute('SELECT password_hash FROM users WHERE id=?',(buyer_id,)).fetchone()
    try:valid = user is not None and hasher.verify(user['password_hash'],password)
    except (VerificationError,InvalidHashError):valid = False
    if not valid:raise RecoveryError(401,'Nieprawidłowe hasło. PIN nie został ujawniony.')
    for order in orders:
        if order['pin_used'] or order['pin_attempts'] >= 5 or order['status'] not in (
            'oczekuje_na_platnosc_testowa','gotowe_do_odbioru_testowo','w_drodze_testowo'):
            raise RecoveryError(409,UNAVAILABLE)
        payment = con.execute('SELECT state,refund_grosze,payout_grosze FROM payment_simulations WHERE order_id=?',(order['id'],)).fetchone()
        if payment and (payment['state'] not in ('awaiting_payment','failed_test','paid_test') or payment['refund_grosze'] or payment['payout_grosze']):
            raise RecoveryError(409,UNAVAILABLE)
        if payment_deadline_passed(con,order['id'],now=now) and (not payment or payment['state'] != 'paid_test'):
            raise RecoveryError(409,UNAVAILABLE)
    row = con.execute('''SELECT c.request_key,c.payload_hash,c.response_json FROM checkout_pin_links l
        JOIN checkout_idempotency c ON c.buyer_id=l.buyer_id AND c.request_key=l.request_key
        WHERE l.order_id=? AND l.buyer_id=?''',(orders[0]['id'],buyer_id)).fetchone()
    if not row:raise RecoveryError(409,UNAVAILABLE)
    try:
        response = vault.open(row['response_json'],buyer_id,row['request_key'],row['payload_hash'],now=now)
        if set(reply_order_ids(response)) != {o['id'] for o in orders} or response.get('shipment_id') != shipment_id:
            raise CheckoutStorageError(UNAVAILABLE)
        field = 'shipment_pin_test_only' if shipment_id else 'pin_test_only'
        pin = response.get(field)
        if not isinstance(pin,str) or not re.fullmatch(r'[0-9]{6}',pin):raise CheckoutStorageError(UNAVAILABLE)
        if any(not hasher.verify(o['pin_hash'],pin) for o in orders):raise CheckoutStorageError(UNAVAILABLE)
    except (CheckoutStorageError,VerificationError,InvalidHashError):raise RecoveryError(409,UNAVAILABLE)
    return {'mode':'test','pin_test_only':pin,'order_ids':[o['id'] for o in orders],
            'shipment_id':shipment_id,'notice':'Sprawdź towar przed przekazaniem PIN-u. Zakup już istnieje; nie składaj go ponownie.'}

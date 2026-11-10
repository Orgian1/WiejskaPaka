"""Opt-in address delivery windows and seller approval, inside order transactions."""
import json
import os
import re
import secrets
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from fastapi import HTTPException, Depends, Header
from pydantic import BaseModel, Field

from backend.checkout_vault import b64, unb64
from backend.local_marketplace import search_key

SCHEMA_SQLITE = '''
CREATE TABLE IF NOT EXISTS seller_delivery_windows (
 id TEXT PRIMARY KEY, farmer_id INTEGER NOT NULL REFERENCES users(id),
 city TEXT NOT NULL, city_key TEXT NOT NULL, postal_code TEXT NOT NULL CHECK(length(postal_code)=6),
 weekday INTEGER NOT NULL CHECK(weekday BETWEEN 0 AND 6),
 start_minute INTEGER NOT NULL CHECK(start_minute BETWEEN 0 AND 1439),
 end_minute INTEGER NOT NULL CHECK(end_minute BETWEEN 1 AND 1440 AND end_minute>start_minute),
 active INTEGER NOT NULL DEFAULT 1 CHECK(active IN (0,1))
);
CREATE INDEX IF NOT EXISTS seller_delivery_windows_farmer ON seller_delivery_windows(farmer_id,active);
CREATE TABLE IF NOT EXISTS address_delivery_requests (
 order_id INTEGER PRIMARY KEY REFERENCES orders(id),
 window_id TEXT NOT NULL REFERENCES seller_delivery_windows(id),
 delivery_date TEXT NOT NULL,
 customer_from INTEGER NOT NULL, customer_to INTEGER NOT NULL,
 agreed_from INTEGER NOT NULL, agreed_to INTEGER NOT NULL,
 state TEXT NOT NULL DEFAULT 'pending' CHECK(state IN ('pending','accepted','declined')),
 revision INTEGER NOT NULL DEFAULT 0 CHECK(revision>=0),
 phone_sealed TEXT NOT NULL,
 CHECK(customer_from>=0 AND customer_to<=1440 AND customer_from<customer_to),
 CHECK(agreed_from>=customer_from AND agreed_to<=customer_to AND agreed_from<agreed_to)
);
'''


def enabled():
    return os.environ.get('WP_ENABLE_ADDRESS_DELIVERY') == '1'


def minutes(text):
    if not isinstance(text, str) or not re.fullmatch(r'(?:[01][0-9]|2[0-3]):[0-5][0-9]', text):
        raise ValueError('Podaj godzinę w formacie GG:MM')
    h, m = map(int, text.split(':'))
    return h * 60 + m


def clock(value):
    return f'{value//60:02d}:{value%60:02d}'


class DeliveryPreferenceIn(BaseModel):
    model_config = {'extra': 'forbid'}
    window_id: str = Field(min_length=32, max_length=32, pattern=r'^[a-f0-9]{32}$')
    delivery_date: str = Field(pattern=r'^[0-9]{4}-[0-9]{2}-[0-9]{2}$')
    available_from: str = Field(pattern=r'^(?:[01][0-9]|2[0-3]):[0-5][0-9]$')
    available_to: str = Field(pattern=r'^(?:[01][0-9]|2[0-3]):[0-5][0-9]$')
    phone: str = Field(strict=True, min_length=9, max_length=24)


class WindowIn(BaseModel):
    model_config = {'extra': 'forbid'}
    city: str = Field(min_length=2, max_length=120)
    postal_code: str = Field(pattern=r'^[0-9]{2}-[0-9]{3}$')
    weekday: int = Field(strict=True, ge=0, le=6)
    from_time: str = Field(pattern=r'^(?:[01][0-9]|2[0-3]):[0-5][0-9]$')
    to_time: str = Field(pattern=r'^(?:[01][0-9]|2[0-3]):[0-5][0-9]$')


class ActiveIn(BaseModel):
    model_config = {'extra': 'forbid'}
    active: bool = Field(strict=True)


class DecisionIn(BaseModel):
    model_config = {'extra': 'forbid'}
    decision: str = Field(pattern=r'^(accepted|declined)$')
    revision: int = Field(strict=True, ge=0)


def has_table(con, postgres=False):
    if postgres:
        return con.execute("SELECT to_regclass('public.address_delivery_requests') AS name").fetchone()['name'] is not None
    return con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='address_delivery_requests'").fetchone() is not None


def prepare(con, payload, farmer_id, *, now=None, postgres=False):
    preference = payload.address_delivery
    if payload.fulfillment != 'dostawa':
        if preference is not None:
            raise HTTPException(422, 'Termin dostawy dotyczy tylko dostawy na adres')
        return None
    if not enabled():
        if preference is not None:
            raise HTTPException(503, 'Terminy dostaw na adres są wyłączone')
        return None
    if preference is None:
        raise HTTPException(422, 'Wybierz termin dostawy, godziny dostępności i podaj numer telefonu')
    row = con.execute('SELECT * FROM seller_delivery_windows WHERE id=? AND farmer_id=? AND active=1' +
                      (' FOR SHARE' if postgres else ''), (preference.window_id, farmer_id)).fetchone()
    if (row is None or row['city_key'] != search_key(payload.delivery_city.strip())
            or row['postal_code'] != payload.delivery_postal_code):
        raise HTTPException(422, 'Sprzedawca nie obsługuje wybranego terminu w tej miejscowości')
    try:
        day = date.fromisoformat(preference.delivery_date)
        instant = (now or datetime.now(timezone.utc)).astimezone(ZoneInfo('Europe/Warsaw'))
        start, end = minutes(preference.available_from), minutes(preference.available_to)
        phone = re.sub(r'[ ()-]', '', preference.phone)
        if not re.fullmatch(r'\+?[0-9]{9,15}', phone):
            raise ValueError('Podaj poprawny numer telefonu')
        if not instant.date() <= day <= instant.date() + timedelta(days=90) or day.weekday() != row['weekday']:
            raise ValueError('Data nie pasuje do dni dostaw sprzedawcy')
        agreed_from, agreed_to = max(start, row['start_minute']), min(end, row['end_minute'])
        if start >= end or agreed_from >= agreed_to:
            raise ValueError('Godziny klienta i sprzedawcy nie mają wspólnego przedziału')
        if day == instant.date():
            agreed_from = max(agreed_from, instant.hour * 60 + instant.minute + 1)
            if agreed_from >= agreed_to:
                raise ValueError('Wybrany termin już minął')
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    return {'window_id': row['id'], 'delivery_date': day.isoformat(),
            'customer_from': start, 'customer_to': end,
            'agreed_from': agreed_from, 'agreed_to': agreed_to, 'phone': phone}


def capture(con, order_id, buyer_id, preference, vault):
    if preference is None:
        return
    nonce = secrets.token_bytes(12)
    aad = f'wp.delivery.phone.v1:{order_id}:{buyer_id}'.encode()
    ciphertext = AESGCM(vault.keys[vault.active]).encrypt(nonce, preference['phone'].encode(), aad)
    envelope = json.dumps({'key_id': vault.active, 'nonce': b64(nonce), 'ciphertext': b64(ciphertext)}, separators=(',', ':'))
    con.execute('''INSERT INTO address_delivery_requests(order_id,window_id,delivery_date,
        customer_from,customer_to,agreed_from,agreed_to,phone_sealed) VALUES(?,?,?,?,?,?,?,?)''',
        (order_id, preference['window_id'], preference['delivery_date'], preference['customer_from'],
         preference['customer_to'], preference['agreed_from'], preference['agreed_to'], envelope))


def require_accepted(con, order_id, *, postgres=False):
    if not has_table(con, postgres):
        return
    row = con.execute('SELECT state FROM address_delivery_requests WHERE order_id=?', (order_id,)).fetchone()
    if row is not None and row['state'] != 'accepted':
        raise HTTPException(409, 'Dostawa wymaga najpierw akceptacji sprzedawcy')


def public_window(row):
    return {'id': row['id'], 'city': row['city'], 'weekday': row['weekday'],
            'postal_code': row['postal_code'],
            'from_time': clock(row['start_minute']), 'to_time': clock(row['end_minute']),
            'active': bool(row['active'])}


def register_routes(app, db, order_write_db, current_user, record_event, *, postgres=False):
    def require_enabled():
        if not enabled():
            raise HTTPException(503, 'Terminy dostaw na adres są wyłączone')

    @app.get('/address-delivery/config')
    def delivery_config():
        return {'enabled': enabled()}

    @app.get('/farmers/{farmer_id}/delivery-windows')
    def windows(farmer_id: int):
        require_enabled()
        with db() as con:
            return {'items': [public_window(row) for row in con.execute(
                'SELECT * FROM seller_delivery_windows WHERE farmer_id=? AND active=1 ORDER BY city,weekday,start_minute,id', (farmer_id,))]}

    @app.get('/address-delivery/windows/mine')
    def my_windows(user=Depends(current_user)):
        require_enabled()
        if user['role'] != 'rolnik':
            raise HTTPException(403, 'Brak uprawnień')
        with db() as con:
            return {'items': [public_window(row) for row in con.execute(
                'SELECT * FROM seller_delivery_windows WHERE farmer_id=? ORDER BY city,weekday,start_minute,id', (user['id'],))]}

    @app.post('/address-delivery/windows')
    def add_window(payload: WindowIn, user=Depends(current_user), authorization: str | None = Header(default=None)):
        require_enabled()
        city = payload.city.strip()
        start, end = minutes(payload.from_time), minutes(payload.to_time)
        if len(city) < 2 or any(ord(c) < 32 for c in city) or start >= end:
            raise HTTPException(422, 'Podaj miejscowość i prawidłowy przedział godzin')
        with order_write_db(user, authorization, ('rolnik',)) as con:
            if con.execute('SELECT count(*) AS n FROM seller_delivery_windows WHERE farmer_id=?', (user['id'],)).fetchone()['n'] >= 200:
                raise HTTPException(409, 'Osiągnięto limit terminów')
            identifier = secrets.token_hex(16)
            con.execute('INSERT INTO seller_delivery_windows(id,farmer_id,city,city_key,postal_code,weekday,start_minute,end_minute) VALUES(?,?,?,?,?,?,?,?)',
                        (identifier, user['id'], city, search_key(city), payload.postal_code, payload.weekday, start, end))
        return {'id': identifier}

    @app.patch('/address-delivery/windows/{window_id}')
    def activate_window(window_id: str, payload: ActiveIn, user=Depends(current_user), authorization: str | None = Header(default=None)):
        require_enabled()
        with order_write_db(user, authorization, ('rolnik',)) as con:
            changed = con.execute('UPDATE seller_delivery_windows SET active=? WHERE id=? AND farmer_id=?',
                                  (int(payload.active), window_id, user['id']))
            if changed.rowcount != 1:
                raise HTTPException(404, 'Nie znaleziono terminu')
        return {'active': payload.active}

    @app.get('/address-delivery/requests/mine')
    def requests(before: int | None = None, user=Depends(current_user)):
        require_enabled()
        if user['role'] not in ('klient', 'rolnik'):
            raise HTTPException(403, 'Brak uprawnień')
        key = 'farmer_id' if user['role'] == 'rolnik' else 'buyer_id'
        if before is not None and before <= 0:
            raise HTTPException(422, 'Nieprawidłowa strona dostaw')
        with db() as con:
            group_expression = "COALESCE(lk.shipment_id,'order:' || CAST(o.id AS TEXT))"
            grouped = con.execute('SELECT '+group_expression+''' AS delivery_group,MAX(o.id) AS last_order
                FROM address_delivery_requests r JOIN orders o ON o.id=r.order_id
                LEFT JOIN shipment_order_links lk ON lk.order_id=o.id WHERE o.''' + key + '=? GROUP BY '+group_expression+
                (' HAVING MAX(o.id)<?' if before is not None else '')+
                ' ORDER BY last_order DESC LIMIT 21', (user['id'], before) if before is not None else (user['id'],)).fetchall()
            rows = []
            for group in grouped[:20]:
                rows.extend(con.execute('''SELECT r.order_id,r.delivery_date,r.customer_from,r.customer_to,
                r.agreed_from,r.agreed_to,r.state,r.revision,o.status,o.pickup_code,
                o.quantity,o.total_grosze,pr.product_name,
                l.delivery_city,l.delivery_street,l.delivery_postal_code,
                lk.shipment_id
                FROM address_delivery_requests r JOIN orders o ON o.id=r.order_id
                JOIN order_locations l ON l.order_id=o.id
                LEFT JOIN shipment_order_links lk ON lk.order_id=o.id
                LEFT JOIN order_purchase_records pr ON pr.order_id=o.id WHERE o.''' + key + '=? AND '+group_expression+
                '=? ORDER BY o.id DESC', (user['id'], group['delivery_group'])).fetchall())
            return {'items': [dict(row) for row in rows],
                    'next_before': grouped[19]['last_order'] if len(grouped)>20 else None}

    @app.post('/address-delivery/requests/{order_id}/decision')
    def decision(order_id: int, payload: DecisionIn, user=Depends(current_user), authorization: str | None = Header(default=None)):
        require_enabled()
        with order_write_db(user, authorization, ('rolnik',)) as con:
            link = con.execute('SELECT shipment_id FROM shipment_order_links WHERE order_id=?', (order_id,)).fetchone()
            if link:
                rows = con.execute('SELECT o.* FROM orders o JOIN shipment_order_links l ON l.order_id=o.id WHERE l.shipment_id=? ORDER BY o.id' +
                                   (' FOR UPDATE OF o' if postgres else ''), (link['shipment_id'],)).fetchall()
            else:
                rows = con.execute('SELECT * FROM orders WHERE id=?' + (' FOR UPDATE' if postgres else ''), (order_id,)).fetchall()
            if not rows or any(o['farmer_id'] != user['id'] for o in rows):
                raise HTTPException(404, 'Nie znaleziono dostawy')
            preferences = [con.execute('SELECT * FROM address_delivery_requests WHERE order_id=?', (o['id'],)).fetchone() for o in rows]
            if any(p is None for p in preferences):
                raise HTTPException(409, 'Niekompletne dane dostawy')
            if all(p['state'] == payload.decision and p['revision'] == payload.revision + 1 for p in preferences):
                return {'state': payload.decision, 'already_processed': True}
            if any(p['state'] != 'pending' or p['revision'] != payload.revision for p in preferences):
                raise HTTPException(409, 'Decyzja została już zmieniona; odśwież zakładkę')
            from backend.inventory_reservations import payment_deadline_passed
            from backend.payment_store import get_payment
            stamp = datetime.now(timezone.utc)
            for order in rows:
                payment = get_payment(con, order['id'])
                if (order['status'] != 'oczekuje_na_platnosc_testowa' or
                    payment_deadline_passed(con, order['id'], now=stamp) or
                    (payment is not None and payment.state not in ('awaiting_payment', 'failed_test'))):
                    raise HTTPException(409, 'Dostawa nie jest już dostępna do akceptacji lub odrzucenia')
            for order in rows:
                con.execute('UPDATE address_delivery_requests SET state=?,revision=revision+1 WHERE order_id=? AND state=? AND revision=?',
                            (payload.decision, order['id'], 'pending', payload.revision))
                if payload.decision == 'declined':
                    con.execute("UPDATE orders SET status='anulowane_testowo' WHERE id=?", (order['id'],))
                    con.execute('UPDATE products SET stock=stock+? WHERE id=?', (order['quantity'], order['product_id']))
                    con.execute('UPDATE inventory_reservations SET released_at=? WHERE order_id=? AND released_at IS NULL',
                                (stamp.isoformat(), order['id']))
                record_event(con, order['id'], user['id'], 'address_delivery_'+payload.decision,
                             order['status'], 'anulowane_testowo' if payload.decision == 'declined' else order['status'])
        return {'state': payload.decision, 'already_processed': False}
